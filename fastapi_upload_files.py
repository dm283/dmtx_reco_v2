import sys, os, time, datetime, shutil, configparser
from typing import Annotated
from fastapi import FastAPI, File, UploadFile, status, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.exceptions import HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from urllib.parse import quote
from pathlib import Path

config = configparser.ConfigParser()
config_file = os.path.join(Path(__file__).resolve().parent, 'config.ini')
if os.path.exists(config_file):
  config.read(config_file, encoding='utf-8')
else:
  print("error! config file doesn't exist"); sys.exit()


PATH_INCOME = config['main']['path_income']
PATH_OUTCOME = config['main']['path_outcome']

# PATH_INCOME = 'c:/Users/dm283/Documents/TECH/ALTA/dmtx-reco-pro/Income'
# PATH_OUTCOME = 'c:/Users/dm283/Documents/TECH/ALTA/dmtx-reco-pro/Outcome'
JOURNAL_FILE = os.path.join(PATH_INCOME, 'journal.txt')

SERVICE_STATUS = 'waiting_new_request'
UPLOADED_FILE = ''

app = FastAPI()


@app.post("/uploadfile/")
async def create_upload_files(request: Request, cnt_elems: Annotated[int, Form()], file: UploadFile):
    global SERVICE_STATUS, UPLOADED_FILE
    
    if cnt_elems < 1:
        return {'ошибка': 'кол-во элементов меньше 1'}

    try:
        filecontent = file.file.read()
        if not os.path.exists(PATH_INCOME):
            os.makedirs(PATH_INCOME)
        file_location = f"{PATH_INCOME}/{file.filename}"


        # проверки файла
        if '.' not in file.filename:
            return {'ошибка': 'не pdf файл'}
        if file.filename.rpartition('.')[2] != 'pdf':
            return {'ошибка': 'не pdf файл'}
        if file.headers['content-type'] != 'application/pdf':
            return {'ошибка': 'не pdf файл'}


        # загрузка файла на сервер в папку Income
        with open(file_location, "wb+") as file_object:
            file_object.write(filecontent)

        # запись в журнал файлов
        current_time = datetime.datetime.now()
        new_record = f'current_time: {current_time};  filename: {file.filename};  cnt_elems: {cnt_elems}\n'
        with open(JOURNAL_FILE, "a") as f:
            f.write(new_record)

        UPLOADED_FILE = file.filename
        SERVICE_STATUS = 'file_uploaded'

    except Exception as e:
        msg = {'status': 'error', 'message': 'file uploading or saving error', 'exception': str(e)}
        print(msg)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f'ошибка загрузки или сохранения файла на сервере')

    content = f"""
        <body style="background-color: #DCDCDC">

        <div style="margin: auto; margin-top: 30px; width: 500px; padding: 20px 40px 10px; 
            border: 1px; border-style: solid; border-radius: 8px; background-color: white; color: black;
            font-weight: 500; font-family: Helvetica, Arial, sans-serif;">

        <div style="margin-bottom: 20px;">Файл {file.filename} принят для обработки.</div>
        <div style="margin-bottom: 20px;">Для проверки готовности и скачивания результата нажмите кнопку ниже.</div>

        <form action="/check_n_download_res/" method="get">
        <input style="width: 100%; height: 40px; background-color: #90EE90; cursor: pointer; font-weight: 200;
            -webkit-border-radius: 5px; border-radius: 5px; border:0 none; font-size:15px;" 
            type="submit" value="ПРОВЕРИТЬ И СКАЧАТЬ">
        </form>

        <form action="/" method="get">
        <input style="width: 100%; height: 40px; background-color: #00BFFF; cursor: pointer; font-weight: 200;
            -webkit-border-radius: 5px; border-radius: 5px; border:0 none; font-size:15px;" 
            type="submit" value="НОВЫЙ ЗАПРОС">
        </form>

        </div>

        </body>
    """
    
    return HTMLResponse(content=content)


@app.get("/check_or_new_view/")
async def check_or_new_view(request: Request):
    content = f"""
        <body style="background-color: #DCDCDC">

        <div style="margin: auto; margin-top: 30px; width: 500px; padding: 20px 40px 10px; 
            border: 1px; border-style: solid; border-radius: 8px; background-color: white; color: black;
            font-weight: 500; font-family: Helvetica, Arial, sans-serif;">

        <div style="margin-bottom: 20px;">Файл {UPLOADED_FILE} принят для обработки.</div>
        <div style="margin-bottom: 20px;">Для проверки готовности и скачивания результата нажмите кнопку ниже.</div>

        <form action="/check_n_download_res/" method="get">
        <input style="width: 100%; height: 40px; background-color: #90EE90; cursor: pointer; font-weight: 200;
            -webkit-border-radius: 5px; border-radius: 5px; border:0 none; font-size:15px;" 
            type="submit" value="ПРОВЕРИТЬ И СКАЧАТЬ">
        </form>

        <form action="/" method="get">
        <input style="width: 100%; height: 40px; background-color: #00BFFF; cursor: pointer; font-weight: 200;
            -webkit-border-radius: 5px; border-radius: 5px; border:0 none; font-size:15px;" 
            type="submit" value="НОВЫЙ ЗАПРОС">
        </form>

        </div>

        </body>
    """
    return HTMLResponse(content=content)


@app.get("/check_n_download_res/")
async def download_res(request: Request):
    global SERVICE_STATUS

    print('SERVICE_STATUS =', SERVICE_STATUS)
    
    if SERVICE_STATUS == 'result_downloaded':
        return RedirectResponse(request.url_for('main'))

    while(True):
        print('[ info ]  ожидание файла с результатом ...')
        time.sleep(2)
        files_list = os.listdir(PATH_OUTCOME);
        for file_name in files_list:
            print(f'[ info ]  поступил файл с результатом {file_name}.')

            # download results
            filename = file_name
            filepath = os.path.join(PATH_OUTCOME, filename)
            response = FileResponse(path=filepath,
                                    headers={"Access-Control-Expose-Headers": "Content-Disposition, File-Name",
                                        "File-Name": quote(os.path.basename(filename), encoding='utf-8'),
                                        "Content-Disposition": f"attachment; filename*=utf-8''{quote(os.path.basename(filename))}"})
            
            SERVICE_STATUS = 'result_downloaded'
            
            return response


@app.get("/")
async def main(request: Request): 
    global SERVICE_STATUS

    if SERVICE_STATUS == 'result_downloaded':
        for f in os.listdir(PATH_OUTCOME):
            os.remove(os.path.join(PATH_OUTCOME, f))
        
    if SERVICE_STATUS in ['waiting_new_request', 'result_downloaded']:

        SERVICE_STATUS = 'waiting_new_request'

        content = """
            <body style="background-color: #DCDCDC">

            <div style="margin: auto; margin-top: 30px; width: 500px; padding: 20px 40px 10px; 
                border: 1px; border-style: solid; border-radius: 8px; background-color: white; color: black;
                font-weight: 500; font-family: Helvetica, Arial, sans-serif;">
            <form action="/uploadfile/" enctype="multipart/form-data" method="post">
            <div style="margin-bottom: 20px;">
                <label style="display: block; margin-bottom: 5px;" for="file">Выберите файл</label>
                <input name="file" type="file" required>
            </div>
            <div style="margin-bottom: 30px;">
                <label style="display: block; margin-bottom: 5px;" for="cnt_elems">Укажите максимальное кол-во элементов на одной странице</label>
                <input name="cnt_elems" type="number" required>
            </div>
            <input style="width: 100%; height: 40px; background-color: #90EE90; cursor: pointer; font-weight: 200;
                -webkit-border-radius: 5px; border-radius: 5px; border:0 none; font-size:15px;" 
                type="submit" value="ОТПРАВИТЬ">
            </form>
            </div>

            </body>
        """
        return HTMLResponse(content=content)
    
    else:
        print('status is', SERVICE_STATUS)
        return RedirectResponse(request.url_for('check_or_new_view'))
