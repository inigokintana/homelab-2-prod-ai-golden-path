FROM python:3.12-alpine
WORKDIR /app
COPY . . 
RUN apk add --no-cache gcc musl-dev libffi-dev libpq-dev python3-dev    
RUN pip install --upgrade pip && pip install -r requirements.txt
RUN scrapy startproject dapr_docs_web && mv dapr_spider.py dapr_docs_web/dapr_docs_web/spiders/.
ENTRYPOINT ["python"]
CMD ["load-into-db-dapr.py"]
