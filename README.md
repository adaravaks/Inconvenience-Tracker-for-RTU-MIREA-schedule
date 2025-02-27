# Inconvenience Tracker for RTU MIREA schedule
###### Stack: Python, FastAPI, APScheduler, PostgreSQL (via psycopg3), Git, Docker + Compose

This is an app designed to <ins>search</ins> for, <ins>keep track</ins> of and <ins>display</ins> different inconveniences in the schedule of RTU MIREA

## Functionality
The intended way of communication with the app is through its API. 
It has four different endpoints:

```GET /inconveniences?name=``` (parameter is required) <br>
***Important: the name of entity must strictly follow pattern of either "АААА-00-00" for student groups or "Фамилия И. О." for professors. Parameter field is case-sensitive and punctuation-sensitive***

Responds with JSON containing inconveniences in schedule of a single entity.
The JSON is sorted by dates, from the start of the semester to the end of it. 
Each date correlates to a list, containing inconveniences occurring at that date, sorted by time.
So basically the structure is as follows: {date: [inconveniences]}

```GET /inconveniences_for_everyone``` <br>
Same as previous endpoint, but returns inconveniences for every professor and every student group in MIREA.
The structure is as follows: {date: {name: [inconveniences]}}

```GET /current_inconveniences_for_everyone?request_uuid=``` (parameter is optional) <br>
***Warning: takes a lot of time to load data (usually 2-4 minutes)***<br>
Similar to previous, but forces the app to request and process fresh data from MIREA website, accounting for possible changes the schedule may have had.
Schedule for each entity has to be requested separately and there are about 8000 entities in total, thus such a long runtime.

***Important: processing the request takes quite some time, but the response is IMMEDIATE.***
The response contains request_uuid, which you can then pass as a parameter to the same endpoint, and it will keep you updated on the status of your request.
When the schedule data is updated and refreshed, passing that same request_uuid to that same endpoint will result in a JSON structured same way as in previous endpoint,
but containing totally fresh and relevant data.

```GET /inconvenience_changes``` <br>
This one is different from the rest, as the response contains not current inconveniences,
but rather the *changes* that the app has noticed while updating/refreshing schedule data.

For example, if the schedule has updated and some professor is now experiencing some sort of inconvenience with it,
the app will notice that and save the data about that change. The structure of response is like this:
[ {data keys and values relevant for a specific change} ].<br>
The changes are sorted by datetime when they were noticed by the app in descending order, so basically most recently noticed are first.

## How to launch
0. Make sure your machine has Git and Docker installed. Make sure your Docker daemon is currently running. (100% sure way is to just launch Docker Desktop app)
1. Open the terminal. Run ```git clone https://github.com/adaravaks/Inconvenience-Tracker-for-RTU-MIREA-schedule```
2. Enter the project directory (on Windows, run ```cd Inconvenience-Tracker-for-RTU-MIREA-schedule```) 
3. Run ```docker compose build```
4. Run ```docker compose up -d```
5. Wait for about 5 minutes for the app to launch. The startup *does* need to take that long, since one of the project requirements was that the app must update and refresh all its data on startup, and that, as I have already said, takes quite some time. So bear with it, be a man.
6. Try accessing ```http://localhost/docs``` to see whether the app has launched or not yet. (or ```<domain-name>/docs``` if you're deploying the app on a remote server)
7. Once the page loads, the app is fully functional. Feel free to utilise it as you please!

If you want to shut down the app, run ```docker compose down```

## About branches
***Important: the branch "master" is the only one that represents the final product. If you're deploying the app, use the master branch***

Branches other than master represent the state of the project during development. For example, branch "level_2"
corresponds to what was required to be implemented on level 2. More explanation about these levels below

## About project requirements
The requirements for this project were initially divided into three levels, with each level having different tasks and ultimately leading me towards general improvement of the app.

Let's dive deeper into the requirements for each level:

### Level 1
«Методы поиска "неудобств" в расписание. Нужно сделать обработку 2-ух - 3-ех типов подобных "узких мест"» <br>
**-- Fully implemented --**

«API для получения доступа к этим методам. Ручки должны принимать необязательный query параметр для фильтрации по названию группы / ФИО преподавателя, смотря кого этот метод исследует.» <br>
**-- Fully implemented --**

«Сборка в docker образ, загрузка его на публичный dockerhub, создание docker-compose файла.» <br>
**-- Fully implemented [(dockerhub)](https://hub.docker.com/repository/docker/adaravaks/inconvenience-finder-for-rtu-mirea-schedule/general) --** <br>
*Note: dockerhub only supports singular docker images in its repositories, but starting from level 2 my app runs as a docker compose stack of 2 images, so **there is only "level 1" version** of Inconvenience Tracker on dockerhub*

### Level 2
«В сервисе реализовать background работу, которая применяет разработанные вами методы к расписанию и сохраняет результаты работы в БД. Она должна запускаться при запуске сервиса, а также по определнному расписанию.» <br>
**-- Fully implemented --**

«Результаты по запросу теперь получаются из имеющейся у вас БД, а не собираются по новой.» <br>
**-- Fully implemented --**

«В качестве БД хотелось бы видеть СУБД серверного типа развертывания (не sqlite), в идеале - postgresql.» <br>
**-- Fully implemented --**

### Level 3
«...клиент на запрос данных не ждет полной обработки, а сразу получает некий идентификатор запроса, с которым в последствии раз в разумный промежуток времени ходит в сервис. Сервис же в это время запускает на фоне выполнение этого запроса и на вопрос клиента отдает статусы этого запроса: сначала идет статус в процессе, потом уже готово, с самим ответом. 
Реализовать вышеописанный алгоритм.» <br>
**-- Fully implemented --**

### Bonus level (wasn't strictly required)
«...модифицировать свой сервис, чтобы он хранил не только последнее состояние, но историю изменения расписаний со временем и позволял наблюдать за улучшениями.» <br>
**-- Fully implemented --**

«Нужно сделать так, чтобы сервис мог одновременно обрабатывать только один запрос, а остальные становились в очередь на ожидание. Клиентам соответственно по id такого запроса будет отдаваться статус "в очереди". В случае получения двух и более одинаковых запросов следует отдавать им один идентификатор, чтобы не выполнять одну и ту же операцию дважды.» <br>
**-- Partially implemented --** <br>
*Note: while working on optimisation, I had the same idea but took different approach.
Further explanation below.*

## The balance between time optimisation and data relevancy
Basically, levels 1 and 3 require the app to return relevant data at the cost of increased response time,
while level 2 requires the app to respond quickly at the cost of data relevancy.

Working on the final version of Inconvenience Tracker, I focused on combining the best from these approaches while also minimising their respective downsides.
Here are the solutions i came up with:

```GET /inconveniences?name=``` returns inconveniences of a single entity and generally doesn't take mich time to fetch fresh data (usually 1-2 seconds).
That's why the app will always prioritise fetching fresh data over pulling it from DB, *unless* the app is currently processing a lot of requests (e.g. refreshing all schedule data),
which is the only case when it will pull data from DB, since fetching a fresh schedule while under high load would severely increase response time.

```GET /inconveniences_for_everyone``` always pulls data from DB, so you might think that this data is likely irrelevant and can't be trusted, but that's *just not true.*
While DB data is not always fresh, it never gets outdated by more than 4 hours. Inconvenience Tracker refreshes all schedule data and rewrites DB based on it at least 6 times a day,
which I believe is enough to keep the data relevant. <br>
Even if not, the app can easily be configured to self-refresh more often just by changing 1 line of code.

```GET /current_inconveniences_for_everyone?request_uuid=``` is the one I'm most proud of. When requested with no parameter, Inconvenience Tracker places in its DB an internal request for gathering all schedule data and building a fresh response. 
When it is done, a request with its corresponding uuid as a parameter can be made to get the refreshed data. 
That's how it works for a single user.
With multiple users things get more interesting - when first user places their refresh-request in the app, the app starts processing it as usual, beginning data gathering process for a fresh response. But if any consequential requests are passed *before the first one is fully processed,*
Inconvenience Tracker will assign these requests to the same refreshing process, which means that when the app finishes building fresh response, all these requests will receive that response.


**An example scenario:** 
1. User 1 requests fresh data on everyone's inconveniences. 
2. The app starts processing that request
3. 30 seconds later User 2 makes the same request
4. 60 more seconds later User 3 makes the same request
5. 30 more seconds later app finishes processing first request and builds a fresh response for it.
6. Since requests 2 and 3 were made while the app was processing request 1, all of them will receive the same response.

**In total:** Inconvenience Tracker built a fresh response in 120 seconds. User 1 got their response in 120 seconds. User 2 got their response in 90 seconds. User 3 got their response in 30 seconds.

See what I'm coming at? Potentially, such way of processing could allow for some users to receive ***absolutely fresh*** data on everyone's inconveniences almost ***immediately***

### And that's not all
Another important detail is that each time the request of any user is fully processed, Inconvenience Tracker updates its DB with the fresh data, so that ***even the DB-pulling endpoint will have access to the freshest and most relevant data.***<br>
Taking that into consideration, we can deduce that a total number of DB-refreshes per day could possibly ramp up from just 6 times to a *couple hundred times.* Daily!

## Conclusion
With all that in mind, I believe that I have succeeded in developing an app that is not just fit for education and entertainment, but is capable of serving its purpose in real production, potentially in cooperation with some other MIREA services.