# SmartCAT CLI Tool
Інструмент командного рядка для роботи з SmartCAT API - платформою для управління проектами перекладу.
За основу взято вже існуючу бібліотеку https://pypi.org/project/smartcat/ від v.zhyliaiev
## Встановлення

Змінні середовища (.env файл):
```
SMARTCAT_USERNAME=your_username
SMARTCAT_PASSWORD=your_password
SMARTCAT_SERVER=eu  # або us
```

## Використання
Основний синтаксис
```
python cli.py [ГЛОБАЛЬНІ_ПАРАМЕТРИ] КОМАНДА [ПІДКОМАНДА] [ПАРАМЕТРИ]
Глобальні параметри

--username - Ім'я користувача SmartCAT
--password - Пароль SmartCAT
--server {eu,us} - Регіон сервера (за замовчуванням: eu)
--env-file PATH - Шлях до .env файлу
```

# Команди
## Управління проектами
### Створення проекту
```
python smartcat_cli.py project create "Назва проекту" SOURCE_LANG TARGET_LANG1 [TARGET_LANG2 ...]

Параметри:

name - Назва проекту
source_lang - Код мови джерела (наприклад: en, uk, ru)
target_langs - Коди цільових мов (один або більше)
--assign-vendor - Призначити виконавцю
--files FILE1 [FILE2 ...] - Файли для прикріплення

Приклад:
python smartcat_cli.py project create "Мій проект" en uk ru --files document.docx manual.pdf
```

### Список проектів
```
python smartcat_cli.py project list
```
### Отримання інформації про проект
```
python smartcat_cli.py project get PROJECT_ID
```
### Оновлення проекту
```
python smartcat_cli.py project update PROJECT_ID [ПАРАМЕТРИ]

Параметри:

--name - Нова назва проекту
--source-lang - Нова мова джерела
--target-langs LANG1 [LANG2 ...] - Нові цільові мови

Приклад:

hpython smartcat_cli.py project update 12345 --name "Оновлена назва" --target-langs uk ru de
```
### Видалення проекту
```
python smartcat_cli.py project delete PROJECT_ID [--force]

Параметри:

--force - Пропустити підтвердження
```
### Статистика проекту
```
python smartcat_cli.py project stats PROJECT_ID
```
### Прикріплення документів до проекту
```
python smartcat_cli.py project attach PROJECT_ID FILE1 [FILE2 ...]

Приклад:

python smartcat_cli.py project attach 12345 document.docx translation.xlsx
```
### Додавання цільової мови
```
python smartcat_cli.py project add-language PROJECT_ID LANGUAGE_CODE

Приклад:
python smartcat_cli.py project add-language 12345 de
```
### Скасування проекту
```
python smartcat_cli.py project cancel PROJECT_ID [--force]
```
### Відновлення проекту
```
python smartcat_cli.py project restore PROJECT_ID
```
## Управління документами
### Отримання інформації про документ

```
python smartcat_cli.py document get DOCUMENT_ID
```
### Видалення документа
```
python smartcat_cli.py document delete DOCUMENT_ID [--force]
```
### Експорт документів
```
python smartcat_cli.py document export DOC_ID1 [DOC_ID2 ...] [--type {target,xliff}]

Параметри:

--type - Тип експорту: target (перекладені файли) або xliff (XLIFF формат)

Приклад:

python smartcat_cli.py document export 12345 67890 --type target
```
### Завантаження результату експорту
```
python smartcat_cli.py document download TASK_ID [--output FILENAME]

Параметри:

--output - Ім'я вихідного файлу (за замовчуванням: export_TASK_ID.zip)

Приклад:

python smartcat_cli.py document download abc123 --output my_translation.docx
```
### Оновлення документа
```
python smartcat_cli.py document update DOCUMENT_ID FILE1 [FILE2 ...]
```
### Перейменування документа
```
python smartcat_cli.py document rename DOCUMENT_ID "Нова назва"
```
### Переклад документа
```
python smartcat_cli.py document translate DOCUMENT_ID TRANSLATION_FILE1 [FILE2 ...]
```
### Статус перекладу
```
python smartcat_cli.py document translate-status DOCUMENT_ID
```
## Коди мов
Використовуйте стандартні ISO коди мов:

- en - англійська
- uk - українська
- ru - російська
- de - німецька
- fr - французька
- es - іспанська
- pl - польська
- тощо

## Підтримувані типи файлів
CLI автоматично визначає тип контенту для файлів. Підтримуються:

- Документи: .docx, .doc, .pdf, .txt
- Таблиці: .xlsx, .xls, .csv
- Веб: .html, .xml
- Переклади: .xliff, .tmx
- Інші формати залежно від підтримки SmartCAT

Усі HTTP відповіді відображаються з кодом статусу та заголовками
JSON відповіді форматуються для читабельності
Файли, які не знайдено, викликають помилку з повідомленням
Операції видалення потребують підтвердження (якщо не використано --force)

### Безпека

Паролі не зберігаються у файлі конфігурації
Використовуйте .env файли для безпечного зберігання облікових даних
Додайте .env до .gitignore у ваших проектах

### Усунення неполадок

- Помилка автентифікації: Перевірте правильність імені користувача та паролю
- Помилка підключення: Переконайтеся, що обраний правильний сервер (eu/us)
- Файл не знайдено: Перевірте шляхи до файлів

### Підтримка
Для отримання довідки по будь-якій команді:
bashpython cli.py --help
python cli.py project --help
python cli.py document --help