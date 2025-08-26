FROM python:3.12-alpine
WORKDIR /app
COPY . . 
RUN apk add --no-cache gcc musl-dev libffi-dev libpq-dev python3-dev    
RUN pip install --upgrade pip && pip install -r requirements.txt
COPY ./.chainlit /app/.chainlit
EXPOSE 8001
CMD ["chainlit", "run", "app.py", "-w", "--host", "127.0.0.1", "--port", "8001"]
#CMD ["/bin/sleep","600"]