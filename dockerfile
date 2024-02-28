FROM python:3.12

ENV TOKEN="" \
	URL="http://127.0.0.1:7860" \
	TZ="America/New_York" \
	APIUSER="" \
	APIPASS="" \
	USER="" \
	PASS=""

WORKDIR /app

# Copy requirements
COPY ./requirements.txt /app/requirements.txt

# Pull in the source code
COPY ./resources /default/resources
COPY ./outputs /default/outputs
COPY . /app

RUN chmod +x /app/docker-entrypoint.sh

ENV USE_GENERATE=true

# Run the bot
ENTRYPOINT [ "/app/docker-entrypoint.sh" ]
