# Backyard Archive · Grounded 2

Статический каталог предметов Grounded 2: оружие, доспехи, тринкеты, строительство и материалы.

## Что находится в репозитории

- `index.html` — весь интерфейс сайта;
- `data.js` — сгенерированная база предметов;
- `build_data.py` — скрипт обновления базы из открытых справочников;
- `render.yaml` — готовая конфигурация для Render Static Site.

Сайт не использует Node.js, базу данных или серверную часть. Его можно разместить как обычный статический сайт.

## Быстрый способ: GitHub → Render через Blueprint

### 1. Создать репозиторий GitHub

1. Откройте [github.com/new](https://github.com/new).
2. Создайте новый репозиторий, например `grounded-2-catalog`.
3. Репозиторий можно сделать публичным или приватным — Render попросит доступ к приватному репозиторию отдельно.
4. Загрузите в корень репозитория эти файлы:

   ```text
   index.html
   data.js
   render.yaml
   build_data.py
   README.md
   ```

   Самый простой вариант: на странице репозитория нажать **Add file → Upload files**, перетащить файлы и сделать **Commit changes**.

### 2. Подключить репозиторий к Render

1. Откройте [dashboard.render.com](https://dashboard.render.com/).
2. Нажмите **New → Blueprint**.
3. Подключите GitHub и выберите репозиторий с сайтом.
4. Render найдёт файл `render.yaml` в корне проекта.
5. Нажмите **Apply** или **Create Blueprint**.
6. Дождитесь окончания deploy.

После этого Render выдаст адрес примерно такого вида:

```text
https://backyard-archive.onrender.com
```

Имя можно изменить в Render Dashboard в настройках сервиса.

## Альтернативный способ: создать Static Site вручную

Если не хотите использовать Blueprint:

1. В Render нажмите **New → Static Site**.
2. Подключите GitHub-репозиторий.
3. Выберите ветку `main`.
4. Укажите настройки:

   ```text
   Build Command: echo "Static site — build step is not required"
   Publish Directory: .
   ```

5. Нажмите **Create Static Site**.

После каждого `git push` Render будет автоматически пересобирать сайт, потому что в `render.yaml` включён `autoDeploy: true`.

## Загрузка через Git

Если Git уже установлен на компьютере:

```bash
git clone https://github.com/ВАШ_ЛОГИН/ВАШ_РЕПОЗИТОРИЙ.git
cd ВАШ_РЕПОЗИТОРИЙ

# Скопируйте сюда index.html, data.js, build_data.py, render.yaml и README.md

git add .
git commit -m "Add Grounded 2 catalog"
git push origin main
```

## Как обновить базу предметов

`index.html` работает с готовым файлом `data.js`, поэтому для обычного deploy запускать Python не нужно.

Если нужно заново собрать данные из источников:

```bash
python -m pip install requests beautifulsoup4
python build_data.py
```

После этого проверьте сайт локально и отправьте обновлённый `data.js` в GitHub:

```bash
git add data.js build_data.py
git commit -m "Update Grounded 2 item data"
git push origin main
```

Render автоматически подхватит новый commit и обновит сайт.

## Локальная проверка

Для проверки не рекомендуется открывать `index.html` двойным кликом, потому что некоторые браузеры ограничивают загрузку локальных JavaScript-файлов. Используйте локальный HTTP-сервер:

```bash
python -m http.server 8000
```

Затем откройте:

```text
http://localhost:8000
```

## Важно

- Сайт полностью статический: отдельный backend или база данных не нужны.
- Изображения предметов загружаются с открытых страниц Grounded Wiki. Если изображение временно недоступно, сайт показывает встроенную запасную иконку.
- Названия предметов оставлены на английском, как в игре и игровых справочниках.
- После первого deploy можно включить собственный домен в Render: **Settings → Custom Domains**.
