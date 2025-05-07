FROM python:3.12-alpine
WORKDIR /app
COPY . . 
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
ENTRYPOINT ["python"]
CMD ["guess_poems_dapr.py"]
