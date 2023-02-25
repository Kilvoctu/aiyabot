FROM python:3.11

ENV TOKEN="" \
	URL="http://127.0.0.1:7860" \
	TZ="America/New_York" \
	APIUSER="" \
	APIPASS="" \
	USER="" \
	PASS=""

WORKDIR /app

# Install dependencies
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Pull in the source code
COPY ./resources /default/resources
COPY ./outputs /default/outputs
COPY . /app

RUN chmod +x /app/docker-entrypoint.sh

# Run the bot
ENTRYPOINT [ "/app/docker-entrypoint.sh" ]
