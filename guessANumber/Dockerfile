FROM node:10
# Папка приложения
ARG APP_DIR=app
RUN mkdir -p ${APP_DIR}
WORKDIR ${APP_DIR}
COPY . .
EXPOSE 3000
CMD ["node", "guess.js"]