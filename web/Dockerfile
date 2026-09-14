FROM python:3.12-slim

WORKDIR /home/myapp

COPY ./requirements.txt /home/myapp/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY ./templates/ /home/myapp/templates/
COPY ./static/ /home/myapp/static/
COPY ./app.py /home/myapp/app.py

ENV MONGO_HOST=mongo \
    MONGO_PORT=27017 \
    MONGO_DB=mydatabase \
    MONGO_COLLECTION=mycollection

EXPOSE 8080

CMD ["python", "/home/myapp/app.py"]
