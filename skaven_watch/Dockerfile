FROM python:3.8-slim

# set working directory
WORKDIR /skaven_watch

# copy skaven_watch contents to container
COPY . /skaven_watch

# install packages
RUN pip install -r requirements.txt

# run main.py when the container launches
CMD ["python", "main.py"]

