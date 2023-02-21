FROM python:3.10

WORKDIR /app

# Install dependencies
COPY ./requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

# Pull in the source code
COPY . /app

# Run the bot
CMD [ "python", "aiya.py" ]
