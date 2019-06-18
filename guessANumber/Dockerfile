FROM mhart/alpine-node:12
# Папка приложения
ARG APP_DIR=app
RUN mkdir -p ${APP_DIR}
WORKDIR ${APP_DIR}
COPY . /app
CMD ["node", "guess.js"]