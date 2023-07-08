from mastodon import Mastodon
from dotenv import load_dotenv
from os import getenv
import mysql.connector
import argparse
from datetime import date, timedelta
import locale

locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8')

arg = argparse.ArgumentParser()
arg.add_argument('type', nargs='?', choices=['Weekly', 'Monthly'])

arguments = arg.parse_args()

load_dotenv()

mastodon = Mastodon(getenv('MASTODON_CLIENT_ID'), getenv('MASTODON_CLIENT_SECRET'), getenv('MASTODON_ACCESS_TOKEN'), 'https://mastorol.es')
mastodon.log_in(username=getenv('MASTODON_USER'), password=getenv('MASTODON_PASSWORD'), scopes=['write:statuses'])

cnx = mysql.connector.connect(user=getenv('MYSQL_USER'), database='verkami_cens', password=getenv('MYSQL_PASSWORD'))
cursor = cnx.cursor()

if arguments.type == 'Weekly':
    today = date.today()
    timeParameter = (today-timedelta(weeks=1),)
elif arguments.type == 'Monthly':
    today = date.today()
    timeParameter = (today.replace(month=today.month-1),)

createdPresalesQuery = """
SELECT presales.name, editorials.name
FROM presales
INNER JOIN editorials ON presales.editorial_id = editorials.id
WHERE start >= %s
"""

cursor.execute(createdPresalesQuery, timeParameter)
startedPresales = cursor.fetchall()

pendingPresalesQuery = """
SELECT presales.name, editorials.name, if(announced_end < CURDATE(), 'Retraso', 'Puntual')
FROM presales
INNER JOIN editorials ON presales.editorial_id = editorials.id
WHERE presales.end is null
AND presales.state NOT In ('Recaudando', 'Abandonado', 'Entregado')
ORDER by presales.start ASC
"""
cursor.execute(pendingPresalesQuery)
pendingPresales = cursor.fetchall()

endingPresalesQuery = """
SELECT presales.name, editorials.name
FROM presales
INNER JOIN editorials ON presales.editorial_id = editorials.id
WHERE end >= %s
"""
cursor.execute(endingPresalesQuery, timeParameter)
endingPresales = cursor.fetchall()

if arguments.type == 'Weekly':
    today = date.today()
    firstDay = today - timedelta(weeks=1)
    lastDay = today - timedelta(days=1)
    title = 'Informe semanal: Del {} de {} al {} de {}'.format(firstDay.day, firstDay.strftime('%B'), lastDay.day, lastDay.strftime('%B'))
elif arguments.type == 'Monthly':
    today = date.today()
    yesterday = today - timedelta(days=1)
    title = 'Informe menusal: {}'.format(yesterday.strftime('%B'))

publication = title
if startedPresales:
    publication += '\nSe han iniciado las siguientes preventas:\n'
    for presale in startedPresales:
        publication += '* {} de {}\n'.format(presale[0], presale[1])

if pendingPresales:
    publication += '\nSe espera la llegada de los siguientes manuales ✈️:\n'
    for presale in pendingPresales:
        publication += '* {} de {} ({})\n'.format(presale[0], presale[1], presale[2])

if endingPresales:
    publication += '\nSe han entregado los siguientes manuales:\n'
    for presale in endingPresales:
        publication += '* {} de {}\n'.format(presale[0], presale[1])

mastodon.status_post(publication)