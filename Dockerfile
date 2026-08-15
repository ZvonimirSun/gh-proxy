FROM guysoft/uwsgi-nginx:python3.7

LABEL maintainer="hunshcn <hunsh.cn@gmail.com>"

RUN pip install flask requests

COPY ./app /app
WORKDIR /app

# Make /app/* available to be imported by Python globally to better support several use cases like Alembic migrations.
ENV PYTHONPATH=/app
ENV GH_PROXY_ASSET_URL=https://zvonimirsun.github.io/gh-proxy/ \
    GH_PROXY_PREFIX=/ \
    GH_PROXY_JSDELIVR=0 \
    GH_PROXY_WHITELIST=""

# Move the base entrypoint to reuse it
RUN mv /entrypoint.sh /uwsgi-nginx-entrypoint.sh
# Copy the entrypoint that will generate Nginx additional configs
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

# Run the start script provided by the parent image tiangolo/uwsgi-nginx.
# It will check for an /app/prestart.sh script (e.g. for migrations)
# And then will start Supervisor, which in turn will start Nginx and uWSGI

EXPOSE 80

CMD ["/start.sh"]
