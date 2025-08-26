FROM python:3.12-alpine
WORKDIR /app
COPY . . 
RUN apk add --no-cache gcc musl-dev libffi-dev libpq-dev python3-dev inotify-tools
RUN pip install --upgrade pip && pip install -r requirements.txt
RUN chmod 755 monitor_docs.sh
CMD ["sh","monitor_docs.sh"]