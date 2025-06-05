FROM python:3.12-alpine
WORKDIR /app
COPY . . 
RUN apk add --no-cache gcc musl-dev libffi-dev libpq-dev python3-dev inotify-tools
RUN pip install --upgrade pip && pip install -r requirements.txt
RUN chnod 755 monitor_docs.sh
#ENTRYPOINT ["python"]
#CMD ["guess-wiki-questions.py"]
CMD ["monitor_docs.sh"]
