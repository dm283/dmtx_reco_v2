import os, sys, shutil, random, configparser, logging, time, zipfile
from pikepdf import Pdf
from pdf2image import convert_from_path
import pylibdmtx.pylibdmtx as dmtx_lib, cv2, datetime, os, sys, csv
from pathlib import Path

config = configparser.ConfigParser()
config_file = os.path.join(Path(__file__).resolve().parent, 'config.ini')
if os.path.exists(config_file):
  config.read(config_file, encoding='utf-8')
else:
  print("error! config file doesn't exist"); sys.exit()


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


PATH_INCOME = 'Income'
PATH_OUTCOME = 'Outcome'
PROCESSINGS_COMMON_FOLDER = 'Processings'
if not os.path.exists(PATH_INCOME):
    os.mkdir(PATH_INCOME)
if not os.path.exists(PATH_OUTCOME):
    os.mkdir(PATH_OUTCOME)
if not os.path.exists(PROCESSINGS_COMMON_FOLDER):
    os.mkdir(PROCESSINGS_COMMON_FOLDER)
TIMEOUT_LIST = [100, 500, 2000, 5000, 10000, ] # 20000, 30000, 50000, None] # full list

JOURNAL_FILE_NAME = 'journal.txt'
JOURNAL_FILE = os.path.join(PATH_INCOME, JOURNAL_FILE_NAME)


def create_processing_folders():
    # creates folders for current processing
    current_processing_folder = datetime.datetime.now().strftime('%Y-%m-%d %H.%M.%S')
    processing_folder = os.path.join(PROCESSINGS_COMMON_FOLDER, current_processing_folder)
    if os.path.exists(processing_folder):
        processing_folder = os.path.join(PROCESSINGS_COMMON_FOLDER, f'{current_processing_folder}({str(random.randint(1, 100))})')
    source_pdf_file_folder = os.path.join(processing_folder, '1_source_pdf_file')
    pdf_pages_folder = os.path.join(processing_folder, '2_pdf_pages')
    jpg_files_folder = os.path.join(processing_folder, '3_jpg_files')
    undecoded_pages_folder = os.path.join(processing_folder, '4_undecoded_pages')
    res_csv_file = os.path.join(processing_folder, 'res_decoded_dmtx.csv')
    log_file = os.path.join(processing_folder, 'log.txt')
    report_file = os.path.join(processing_folder, 'bot_report.txt')

    for folder in [processing_folder, source_pdf_file_folder, pdf_pages_folder, jpg_files_folder, undecoded_pages_folder]:
        os.mkdir(folder)

    return processing_folder, source_pdf_file_folder, pdf_pages_folder, jpg_files_folder, res_csv_file, log_file, report_file, undecoded_pages_folder


def split_pdf_to_pages(source_pdf_file, pdf_pages_folder):
    # load source pdf file and split it to distinct pages
    print('load pdf file ...', end=' ')
    pdf = Pdf.open(source_pdf_file)
    print('ok. source pdf file pages =', len(pdf.pages))

    print('splitting file to distinct pages ...')
    for n, page in enumerate(pdf.pages):
        print(n, end='\r')
        dst = Pdf.new()
        dst.pages.append(page)
        dst.save(f'{pdf_pages_folder}/{n}.pdf')
    print(f'ok. splitted to {n+1} pages')


def convert_pdf_to_jpg(pdf_pages_folder, jpg_files_folder, dmtx_cnt_per_page):
    # convert pdf pages to jpg files
    counter = int()

    # if elements quantity per page is 1 then set dpi = 400, else 200 
    # (because not every elements is decoded if dpi 400 and quantity of element 20 for example)
    dpi = 400 if dmtx_cnt_per_page == 1 else 200
        
    pdf_files = os.listdir(pdf_pages_folder)
    pdf_files.sort(key=lambda x: int(x.partition('.')[0]))

    print('converting pdf to jpg ...')
    for file in pdf_files:
        print(file, end='\r')
        image = convert_from_path( os.path.join(pdf_pages_folder, file), dpi=dpi, )
        image[0].save(f'{jpg_files_folder}/page'+ str(counter) +'.jpg', 'JPEG')
        counter += 1
    print(f'ok. converted {counter} files')


def save_list_to_csv(source_list, res_csv_file):
    # save list to csv file
    rows_for_csv = [ [e] for e in source_list ]

    print('saving results to csv file ...', end=' ')
    with open(res_csv_file, 'w', newline='') as f:
        write = csv.writer(f, delimiter=' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        write.writerows(rows_for_csv)
    print(f'ok. saved to {res_csv_file} file')


def save_log(log_dict, log_file):
    # save file - res records
    print('saving logs ...', end=' ')
    with open(log_file, 'w') as f:
        for k in log_dict:
            rec = f'{k} - decoded {len(log_dict[k])} datamatrixes' + '\n'
            f.write(rec)
    print(f'ok. saved to {log_file} file')


def makeup_report(log_dict, dmtx_cnt_per_page, report_file, undecoded_pages_folder, pdf_pages_folder):
    # makes up a report with quantity of un-/successful handlings of pages
    cnt_pages = int()
    cnt_elems = int()
    # wrong_pages_list = list()
    cnt_unreco_partly = int()
    cnt_unreco_totally = int()
    substr_report_unreco_pages = str()
    substr_report_decoded_elems = str()

    for k in log_dict:
        cnt_pages += 1
        cnt_decoded_elems = len(log_dict[k])
        cnt_elems += cnt_decoded_elems
        if cnt_decoded_elems < dmtx_cnt_per_page:
            page_name = k.partition('.')[0][4:]
            # wrong_pages_list.append(page_name)
            substr_report_unreco_pages += f'\n[ page-{page_name} ]: {cnt_decoded_elems}'

            substr_elems_list = str()
            for n, e in enumerate(log_dict[k]):
                s = f"\n{' '*20+' '*len(page_name)}" if n > 0 else ''
                substr_elems_list += f'{s}{n}) {e}'

            if cnt_decoded_elems == 0:
                cnt_unreco_totally += 1
            else:
                cnt_unreco_partly += 1
                substr_report_decoded_elems += f'\n[ page-{page_name} ]:    {substr_elems_list}'
            
            # copying un/partly recognized pages into sprcial folder
            file_name_source = f'{pdf_pages_folder}/{page_name}.pdf'
            file_name_distance = f'{undecoded_pages_folder}/{page_name}.pdf'
            if os.path.exists(file_name_source):
                shutil.copyfile(file_name_source, file_name_distance)            

    report_text = f"""=== ОТЧЕТ БОТА ===\n
обработано страниц всего:            {cnt_pages} (по {dmtx_cnt_per_page} элемента на страницу максимально)
распознано элементов:                  {cnt_elems} 
распознано страниц полностью: {cnt_pages - cnt_unreco_partly - cnt_unreco_totally} 
распознано страниц частично:    {cnt_unreco_partly} 
нераспознано страниц:                 {cnt_unreco_totally} 
"""
    if substr_report_unreco_pages or substr_report_decoded_elems:
        report_text += '\nвнимание (!) - нумерация страниц в следующих списках начинается с нуля (0)\n'
    if substr_report_unreco_pages:
        report_text += f'\nнераспознанные/частично распознанные страницы и кол-во успешно распознанных элементов:\
{substr_report_unreco_pages}'
    if substr_report_decoded_elems:
        report_text += f'\n\nраспознанные элементы на частично распознанных страницах:\
{substr_report_decoded_elems}'

    with open(report_file, 'w') as f:
        f.write(report_text)

    # archivates pages files
    print('ARCHIVATING....')
    files_for_archiving = os.listdir(undecoded_pages_folder)
    if files_for_archiving:
        with zipfile.ZipFile(f'{undecoded_pages_folder}/undecoded_pages.zip', mode='w') as archive:
            for file in files_for_archiving:
                print(file)
                archive.write(filename=f'{undecoded_pages_folder}/{file}', arcname=file)

    return report_text #, wrong_pages_list


def decode_jpg_dmtx(jpg_files_folder, timeout_dmtx_decode, dmtx_cnt_per_page):
    #  decodes datamatrix form jpg file
    general_decode_list = list()
    log_dict = dict()
    jpg_files = os.listdir(jpg_files_folder)
    jpg_files.sort(key=lambda x: int(x.partition('.')[0][4:]))

    print('decoding datamartixes ...')
    for file in jpg_files:
        # print(file, end='\r')
        print(file, end=' ')
        image = cv2.imread( os.path.join(jpg_files_folder, file) )

        # decode_list = [ r.data.decode() for r in dmtx_lib.decode(image, timeout=timeout_dmtx_decode) ]

        timeout = timeout_dmtx_decode
        decode_list = list()
        # TIMEOUT_LIST = [100, 500, 2000, 5000, 10000, 20000, 30000, 50000, None]
        timeout_list_pointer = TIMEOUT_LIST.index(timeout_dmtx_decode)
        while len(decode_list) < dmtx_cnt_per_page:
            decode_list = [ r.data.decode() for r in dmtx_lib.decode(image, timeout=timeout) ]
            print( 'decoded elements =', len(decode_list) )
            if len(decode_list) < dmtx_cnt_per_page:
                timeout_list_pointer += 1
                if (timeout_list_pointer + 1) <= len(TIMEOUT_LIST):
                    timeout = TIMEOUT_LIST[timeout_list_pointer]
                    print(file, f'increase timeout to {timeout}')
                    print(file, end=' ')
                else:
                    print(file, 'maximum timeout')
                    break


        log_dict[file] = decode_list
        general_decode_list += decode_list
    print(f'ok. decoded { len(general_decode_list) } datamartixes')

    return general_decode_list, log_dict


def timeout_count(dmtx_cnt_per_page):
    # estimates timeout for dmtx decoding
    #TIMEOUT_DMTX_DECODE = 2000  # dmtx on page - timeout    20 - 2000   10 - 500   5 - 100   1 - 100
    if dmtx_cnt_per_page <= 20:
        timeout_dmtx_decode = 2000
    if dmtx_cnt_per_page <= 10:
        timeout_dmtx_decode = 500
    if dmtx_cnt_per_page <= 5:
        timeout_dmtx_decode = 100
    if dmtx_cnt_per_page > 20:
        timeout_dmtx_decode = 2000 # None
    print(f'dmtx_quantity = {dmtx_cnt_per_page}  timeout = {timeout_dmtx_decode}')

    return timeout_dmtx_decode


def income_elems_per_page_cnt_check(caption):
    # checks correct format of caption
    try:
        dmtx_cnt_per_page = int(caption)
        if dmtx_cnt_per_page < 1:
            raise Exception
    except:
        return 'err', None
    
    return 'ok', dmtx_cnt_per_page


def create_res_outcome(processing_folder, undecoded_pages_folder, income_pdf_file_name):
    #
    print('creating results outcome archive ...', end=' ')
    print('processing_folder =', processing_folder)

    filenamepostfix = processing_folder.partition('\\')[2]

    files_list = ['bot_report.txt', 'log.txt', 'res_decoded_dmtx.csv']
    if os.path.exists(f'{undecoded_pages_folder}/undecoded_pages.zip'):
        files_list.append('4_undecoded_pages/undecoded_pages.zip')

    with zipfile.ZipFile(f'{processing_folder}/{income_pdf_file_name}.zip', mode='w') as archive:
        for file in files_list:
            archive.write(filename=f'{processing_folder}/{file}', arcname=file)
    shutil.copyfile( f'{processing_folder}/{income_pdf_file_name}.zip', 
                    os.path.join(PATH_OUTCOME, f'{income_pdf_file_name+filenamepostfix}.zip') )
    print('ok.')


def run_reco_script(income_pdf_file_name, dmtx_cnt_per_page):
    #
    timeout_dmtx_decode = timeout_count(dmtx_cnt_per_page)

    print('run script', 'file =', 'file_name', 'timeout_dmtx_decode = ', timeout_dmtx_decode, 'dmtx_cnt_per_page = ', dmtx_cnt_per_page)
    
    processing_folder, source_pdf_file_folder, pdf_pages_folder, jpg_files_folder, res_csv_file, log_file, \
            report_file, undecoded_pages_folder = create_processing_folders()

    source_pdf_file = os.path.join(source_pdf_file_folder, income_pdf_file_name)

    # create foo - save source_pdf_file to source_pdf_file_folder
    income_pdf_file = os.path.join(PATH_INCOME, income_pdf_file_name)
    shutil.copyfile(income_pdf_file, source_pdf_file)

    message_text = 'принято. ожидайте ответа'
    print(message_text)

    # common functions - incoming pdf file handling and decoding of datamatrixes
    split_pdf_to_pages(source_pdf_file, pdf_pages_folder)
    convert_pdf_to_jpg(pdf_pages_folder, jpg_files_folder, dmtx_cnt_per_page)
    general_decode_list, log_dict = decode_jpg_dmtx(jpg_files_folder, timeout_dmtx_decode, dmtx_cnt_per_page)
    save_list_to_csv(general_decode_list, res_csv_file)
    save_log(log_dict, log_file)
    makeup_report(log_dict, dmtx_cnt_per_page, report_file, undecoded_pages_folder, pdf_pages_folder)

    create_res_outcome(processing_folder, undecoded_pages_folder, income_pdf_file_name)


def remove_record_from_journal(file_name):
    #
    with open(JOURNAL_FILE, 'r+') as fp:
        lines = fp.readlines()
        fp.seek(0)
        fp.truncate()
        for number, line in enumerate(lines):
            if file_name not in line:
                fp.write(line)


######
if __name__ == '__main__':

    while(True):
        print('[ info ]  ожидание нового файла ...')
        time.sleep(5)
        if len(os.listdir(PATH_INCOME)) < 1:
            continue

        files_list = os.listdir(PATH_INCOME); files_list.remove(JOURNAL_FILE_NAME)
        for file_name in files_list:
            print(f'[ info ]  поступил новый файл {file_name}.')

            income_pdf_file_name = file_name

            time.sleep(3)
            # чтение из журнала кол-ва элементов для файла
            with open(JOURNAL_FILE) as f:
                while True:
                    line = f.readline()
                    if len(line) == 0:
                        print('error - empty journal'); sys.exit()
                    if file_name in line:
                        break
                cnt_elems = int(line.partition('cnt_elems: ')[2].strip())
            print('file_name =', file_name, 'cnt_elems =', cnt_elems)
    
            # основной скрипт обработки
            run_reco_script(income_pdf_file_name, dmtx_cnt_per_page=cnt_elems)

            # удаление файла из папки Income
            file_for_deleting = os.path.join(PATH_INCOME, file_name)
            os.remove(file_for_deleting)
            print('файл удалён')

            # удаление записи из журнала
            remove_record_from_journal(file_name)
            print('запись из журнала удалена')
