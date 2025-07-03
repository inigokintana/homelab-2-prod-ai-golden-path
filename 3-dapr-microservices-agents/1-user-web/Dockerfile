FROM python:3.12-alpine
WORKDIR /app
COPY . . 
RUN apk add --no-cache gcc musl-dev libffi-dev libpq-dev python3-dev    
RUN pip install --upgrade pip && pip install -r requirements.txt
ENTRYPOINT ["python"]
CMD ["app-dapr.py"]