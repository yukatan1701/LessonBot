# LessonBot
Бот предназначен для проведения тестирований в Discord.

## Установка и подключение
Требования:
* Python 3.8.
* Установленные пакеты *discord.py* и *python-dotenv*. Чтобы установить эти пакеты, выполните следующие действия:
```
$ pip install -U discord.py
$ pip install -U python-dotenv
```

Шаги:
1. Перейдите на [Discord Developer Portal](https://discord.com/developers) в браузере.
2. Нажмите на кнопку **New Application**.
3. Назовите приложение **LessonBot**.
4. Перейдите на вкладку **Bot**, нажмите на кнопку **AddBot**.
5. Перейдите на вкладку **OAuth2**. В области **Scopes** поставьте галочку около **bot**. В области **Bot Permissions** выберите **Administrator**. Не забывайте сохранять внесенные изменения.
6. После выполнения этих действий между областями **Scopes** и **Bot Permissions** появится ссылка. Скопируйте ее и перейдите по ней. В появившемся окне выберите сервер, на который желаете пригласить бота.
7. Вернитесь на Discord Developer Portal. Перейдите на вкладку **Bot**. В разделе **Privileged Gateway Intents** активируйте **Presence Intent** и **Server Members Intent**. В разделе **Token** нажмите на кнопку **Copy**. Никому не сообщайте этот токен! В случае утечки токена нажмите на кнопку **Regenerate**.
7. В директории с исходным кодом бота откройте файл *.env*. Вставьте в конец первой строки после `DISCORD_TOKEN=` скопированный токен. На второй строке после `DISCORD_GUILD=`вставьте название сервера, на который вы пригласили бота. Сохраните документ.
8. После этого запустите скрипт бота:
```
$ python bot.py
```
Если подключение прошло успешно, вы увидите похожее сообщение:
```
STAT_FILE_PATH: /home/user/statistics.txt
...
LessonBot has connected to Discord!
LessonBot#3602 has connected to the following guild:
LessonBotServer(id: 00000000000000000000)
Guild Members:
 - Vasya777
 - Pupa
 - Lupa
Member list was loaded successfully.
```
Если при подключении произошла ошибка или список участников сервера содержит только бота, проверьте, все ли шаги вы выполнили правильно.
9. Перейдите в настройки сервера, на который вы пригласили бота. Выберите раздел **Роли**. Нажмите **Создание роли**. Назовите роль **admin**. Во вкладке **Права доступа** активируйте вариант **Администратор**. В качестве участника добавьте себя.

## Формат вопросов
Перед проведением тестирования подготовьте список команд для генерации вопросов тестирования. Каждая команда должна иметь следующий вид:
```
/quiz ?:Вопрос +:Правильный ответ =:Неправильный ответ
```
Текст вопроса должен начинаться с префикса `?:`, текст правильного ответа с `+:`, а неправильного - с `=:`. Правильных и неправильных вариантов ответа может быть несколько. Текст вопроса или варианта ответа - это текст, заключенный между соседними префиксами, не считая пробельных символов по краям. Допустимо разбивать текст вопроса/ответа на несколько строк.

Вариант оформления вопроса теста, в котором вопрос и варианты ответов начинаются с новой строки:
```
/quiz
?:Вопрос
+:Правильный ответ
=:Неправильный ответ
```
Вариант оформления вопроса теста, включающий разбиение текста вопроса и вариантов ответов несколько строк:
```
/quiz
?:Длинный вопрос
на несколько строк???

+:Правильный ответ,
очень длинный правильный ответ.

=:Неправильный ответ
на две строки.
```

## Использование
Чтобы начать тестирование, убедитесь, что бот находится онлайн, то есть что вы запустили на исполнение скрипт *bot.py*. Как уже упоминалось ранее, в случае успешного запуска вы увидите в консоли список участников сервера. 

Запуск тестирования производится с помощью команды `/start`, которую нужно набрать в любом из текстовых каналов сервера. В результате выполнения этой команды будет сформирована категория *Тестирование*, в которой для каждого пользователя, подключенного к голосовому чату, создастся приватный канал. Имя каждого канала состоит префикса **test\_** и имени пользователя. Для администратора создастся отдельный канал с префиксом **\_admin\_**. Администратору (то есть вам) нужно перейти в этот канал, чтобы продолжить работу.

После того, как вы перешли в свой канал, скопируйте первую из ранее вами созданных команд и отправьте ее как сообщение. Например:
```
/quiz ?:Какого цвета луна? +:Белая =:Зеленая =:Малиновая
```
Сначала вам, а потом всем участникам тестирования разошлется сгенерированная форма вопроса. Для вас, администратора, появится еще и статистика ответа на вопрос. По мере того, как участники будут отвечать на вопросы, статистика будет обновляться. Чтобы посмотреть текущую статистику *по всем вопросам теста*, наберите команду `/stat`. Чтобы отправить следующий вопрос, снова используйте команду `/quiz`.

После того, как тест будет завершен, наберите команду `/stop`. Эта команда соберет статистику во всем вопросам, пришлет ее администратору, сохранит в файл (по умолчанию *statistics.txt* в директории бота), а затем удалит вопросы и ответы из памяти бота. Чтобы посмотреть итоговую статистику еще раз, используйте команду `/stat`. Пока вы не начнете новое тестирование, эта команда будет показывать результаты последнего тестирования.

Чтобы очистить список каналов тестирования, используйте команду `/clear`.

## Детальная настройка
Для более детальной настройки вы можете изменять файл *.env*, который имеет следующую структуру:
```
DISCORD_TOKEN=
DISCORD_GUILD=
TESTING_PREFIX=test_
TESTING_ADMIN_PREFIX=_admin_
TESTING_CATEGORY=тестирование
STAT_FILE_PATH=
```
* `DISCORD_TOKEN` - это токен, который нужен для подключения бота.
* `DISCORD_GUILD` - это название сервера, к которому подключается бот.
* `TESTING_PREFIX` - префикс, который используется при генерации текстовых каналов для проведения тестирования. У всех пользователей, кроме администратора, название канала будет состоять из этого префикса и ника пользователя на сервере. Например: *test_vasya777*.
* `TESTING_ADMIN_PREFIX` - это префикс, который используется при генерации текстового канала для администратора.
* `TESTING_CATEGORY` - название категории, которая будет создана для объединения текстовых каналов тестирования.
* `STAT_FILE_PATH` - путь к файлу, в который будет сохраняться статистика. Если в качестве этого параметра задан путь к директории, статистика будет сохраняться в файл *statistics.txt* внутри нее. Если значение параметра отсутствует или параметр задан некорректно, будет использоваться путь по умолчанию - текущая директория, статистика будет сохраняться в файл *statistics.txt*. 