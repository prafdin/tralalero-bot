# 🧠 Voice Quiz Telegram Bot
[![ChatGPT](https://img.shields.io/badge/ChatGPT-4.0-blue?style=flat&logo=OpenAI)](https://openai.com/chatgpt)

Бот для проведения голосового квиза по персонажам вселенной [Brainrot Wiki](https://brainrot.fandom.com).

## 🚀 Возможности

- 📸 Отображает картинку с персонажем.
- 🎙 Принимает только голосовые ответы.
- 🔊 Отправляет эталонное произношение.
- 🤖 Распознаёт речь с помощью Yandex SpeechKit.
- 🧮 Сравнивает ответ с правильным и начисляет баллы.
- 🏁 Подводит итоги после всех вопросов.

## 📦 Установка и запуск

### 1. Клонирование репозитория
```bash
git clone https://github.com/prafdin/tralalero-bot.git
cd tralalero-bot
git lfs pull
```
### 2. Настройка токенов
```bash
cp .env.example .env
vi .env
```
### 3. Сборка контейнера
```bash
docker build -t tralalero-bot .
```
### 4. Запуск контейнера
```bash
docker run -d \
  --env-file .env \
  --restart unless-stopped \
  tralalero-bot
```

## ⚙️ Технологии
- Python 3.11+
- python-telegram-bot
- Yandex SpeechKit
- FuzzyWuzzy
- Docker 
