import requests
import json
import telebot
from collections import Counter
from functools import lru_cache


bot = telebot.TeleBot = ('БОТ ТОКЕН') 

try:
    heroes_data = requests.get("https://api.opendota.com/api/heroes", timeout=10).json() #Создаем переменную heroes_data, которая будет отвечать за список героев, если ответа не
    #будет за 10 секунд - "курьер" в виде функции .get() уйдет с сайта без данных
    heroes_dict = {hero['id']: hero['localized_name'] for hero in heroes_data } #создаем список , который будет отвечать за название всех героев по ID на сайте opendota'ы , например 1. Anti-mage и т.д. цикл for
    #проделывает это для каждого героя в heroes_data
except:
    heroes_dict = {} #если не получится получить от "курьера" данные heroes_data , создать пустой список
@lru_cache(maxsize=128)
def get_account_id(steam_id): #создаем функцию, которая будет определить айди аккаунта
    try:
        steam_id = str(steam_id).strip() # переобразует переменную в строку, например, если пользователь вводит "   id    ", то данная переменная перводит все в "id"
        if not steam_id.isdigit(): # если steam_id НЕ цифры, то функция возвращает None 
                return None
            
        steam_id_num = int(steam_id) # создает переменную steam_id в форме int
        if len(steam_id) == 17: #Если steam_id 64-битный, т.е. имеет 17 символов, то функция переведет в 32-битный, вычтев 76561197960265728(номер первого аккаунта)
            return steam_id_num - 76561197960265728
        elif len(steam_id) <= 10 : #Если пользователь ввел код меньше или = 10, то код вернет число неизменняя его, т.к. это 32-битная система
            return steam_id_num
        else: 
            return None #Если не удалось распознать steam_id, например, оно состоит из  11 символов, то функция вернет None 
        
    except (ValueError, TypeError) as e:
        print(f"Error {e}")
        return None #Если возникнет ошибка при попытке, функция вернет None

def get_info_player(account_id):
    try: #пытаемся выполнить функцию
        url = f"https://api.opendota.com/api/players/{account_id}" # записываем url в переменную, дабы было удобнее использовать в функции
        response = requests.get(url, timeout=10) #отправляем запрос на сервер opendota, дабы получить данные о игроке
        
        if response.status_code == 200: # status_code это коды, которые означают статус полученных данных с сайта, 200 - успех, 404 - ошибка, 500 - проблема на сервере сайта, 429  - слишком долго ожидание
            return response.json()#переводим данные в удобный формат, который можно дальше использовать
        else: 
            print(f"Ошибка API: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:# ловим ошибки сети, таймауты и т.д.
        print(f"Ошибка соединения: {e}")
        return None # если не получилось взять данные - возвращаем None
    
def analyz_matches(account_id):
    url = f'https://api.opendota.com/api/players/{account_id}/matches' # указываем ссылку в переменную, дабы далее удобнее использовать в функции
      
    params = {'limit': 50} # указываем лимит игр, которые будут обрабатываться
    try: # попытка произвести функцию, которая может поломаться 
        response = requests.get(url, params=params, timeout=15) # отправляем запрос на сервер, который будет выполняться до 15 секунд, если время запроса будет больше 15 сек - запрос прервется
        # просим у сервера данные за 50 последних игр
        matches = response.json() #переводим полученные данные с сервера в python-список, с помощью json()
    except Exception as e: #если возникает ошибка - выводим ее и возвращаем None
        print(f"Error fetching matches: {e}")
        return None
    if not matches or not isinstance(matches, list): #если  matches ложное(None, пустой список, 0, False, 0.0) или matches НЕ лист - вернуть None
        return None
    
    valid_matches = [] #содаем пустой список, куда далее будем записывать данные
    for m in matches: # делаем цикл for, чтобы проделать определенное дело для каждого объекта списка matches
        duration = m.get('duration', 0) # делаем переменную duration, которая будет отвечать за время игры, получая их через метод .get(), если не удалось получить duration - переменная будет равна нулю
        if duration > 300: #если  длительность матча больше 300 секунд записывать  в список m
            valid_matches.append(m) #добавление матчей, длинее 5 минут в список 
    
    total_matches = len(valid_matches) #считаем количество прощедщих фильтрацию матчей, а также записываем их в новую переменную

    wins = 0 #создаем "ведра" или пустые значения, для того чтобы потом их наполнить данными и произвести нужные расчеты, например, расчет среднего gpm и т.д.
    #в wins будем =+ 1, а в остальные списки просто добавлять переменные
    kills = []
    deaths = []
    assists = []
    gpm_list = []
    xpm_list = []
    hero_damage_list = []
    last_hits_list = []
    durations = []
    
    hero_stats = {} #создаем пустой dict, для дальнейших записей в него
    lane_roles = Counter()  #создаем переменную, которая будет считать количество игр , сыгранное на определенной роли, например:
    # список [mid, mid, carry], метод Counter создает следующий списко: {carry: 1, mid: 2 }
    
    for match in valid_matches: #создаем цикл for, который перебирает каждую переменную и что-либо делает с ней в списке matches
        player_slot = match.get('player_slot', 128) #создаем переменную player_slot, которая с помощью метода .get() возьмет с url данные 'player_slot', если у "курьера" это не получится, то он вернется с 128 
        # 0-127 = Radiant, 128-255 = Dire
        radiant_win = match.get('radiant_win', False) #отправляем запрос, где просим найти победу radiant в определенной игре, если данные не удалось получить, то возвращаем False, что означает, что либо Radiant проиграли, либо данные еще не пришли на сервер
        is_winner = (player_slot < 128 and radiant_win) or (player_slot >= 128 and not radiant_win) #ЭТО ПОБЕДИТЕЛЬ если player_slot < 128 (т.е игрок находится в radiant, и если эта команда победила)
    # или player_slot больше или ровно 128 и Radiant проиграли, т.е. игрок находился в dire и dire победили
        if is_winner: #Узнаем из переменной сверху победитель ли это? если это так, добавляем к wins +1
            wins += 1
        kills.append(match.get('kills', 0)) #берём из списка match данные kills(и другие) через .get(), а после добавляем их в список kills(и также с другими)
        gpm_list.append(match.get('gold_per_min', 0)) #а после, выбираем среднее арефметическое
        deaths.append(match.get('deaths', 0))
        assists.append(match.get('assists', 0))
        xpm_list.append(match.get('xp_per_min', 0))
        durations.append(match.get('duration', 0))
        hero_damage_list.append(match.get('hero_damage', 0))
        last_hits_list.append(match.get("last_hits", 0))
    
        hero_id = match.get('hero_id') #отправляем "курьера" на склад match, где он забирает hero_id
        if hero_id: #если hero_id нет - код далее не выполняется, а если есть, выполняется
            if hero_id not in hero_stats: #если такого hero_id нету в hero_stats, добавляем его и его статистику в виде словаря
                hero_stats[hero_id] = {'games': 0, 'wins': 0}
            hero_stats[hero_id]['games'] += 1 #добавляем +1 игру на герое
            if is_winner: #добавляем +1 победу на герое
                hero_stats[hero_id]['wins'] += 1 
        lane_role = match.get('lane_role', 0) #посылаем курьера на склад, где он берёт данные о том, на какой линии стоял игрок, если этих данных нет, возвращаем 0
        lane_roles[lane_role] += 1 #добавляем данные о игре на определенной роли
    
    win_rate = (wins / total_matches) * 100 if total_matches > 0 else 0 #высчитываем процент побед
    avg_kills =  sum(kills) / len(kills) if kills else 0  #высчитываем средние арефметическое
    avg_deaths = sum(deaths) / len(deaths) if deaths else 0
    avg_assists = sum(assists) / len(assists) if assists else 0
    avg_gpm = sum(gpm_list) / len(gpm_list) if gpm_list else 0
    avg_durations = sum(durations) / len(durations) if durations else 0
    avg_hero_damage = sum(hero_damage_list) / len(hero_damage_list) if hero_damage_list else 0
    avg_last_hits = sum(last_hits_list) / len(last_hits_list) if last_hits_list else 0
    avg_xpm = sum(xpm_list) / len(xpm_list) if xpm_list else 0
    
    total_kills = sum(kills)
    total_deaths = sum(deaths)
    total_assists = sum(assists)
    kda = (total_kills + total_assists) / max(total_deaths, 1) #КДА за все матчи  (убийства + помощи) / смерти (защита от деления на 0)
    
    def match_score(match):
        kills = match.get('kills', 0)
        deaths = match.get('deaths', 0)
        assists = match.get('assists', 0)
        gpm = match.get('gold_per_min', 0)
        xpm = match.get('xp_per_min', 0) 
        kda_score = (kills + assists * 0.7) / max(deaths, 1)
        economy_score = (gpm / 400 + xpm / 300) #высчитываем match score, чтобы в дальнейшем применить для показа лучшей/худшей игры
        return kda_score + economy_score
    best_game = max(valid_matches, key=match_score) if valid_matches else None
    worst_game = min(valid_matches, key=match_score) if valid_matches else None #находим лучшую/худшую игру
    
    best_hero = None
    best_hero_winrate = 0
    for hero_id, stats in hero_stats.items(): #возвращаем словарь python , для дальнейших взаимодействий с ним
        if stats['games'] >= 2: 
            winrate = (stats['wins'] / stats['games']) * 100
            if winrate > best_hero_winrate:
                best_hero_winrate = winrate #находим лучшего героя
                best_hero = hero_id 
    
    most_played_hero = max(hero_stats.items(), key=lambda x: x[1]['games']) if hero_stats else None 
    
    if not valid_matches:
        return None
    
    return {
        'total_matches': total_matches,
        'wins': wins,
        'win_rate': win_rate,
        'avg_kills': avg_kills,
        'avg_deaths': avg_deaths,
        'avg_assists': avg_assists,
        'kda_ratio': kda,
        'avg_gpm': avg_gpm,
        'avg_xpm': avg_xpm,
        'avg_duration': avg_durations,
        'avg_hero_damage': avg_hero_damage,
        'avg_last_hits': avg_last_hits,
        'best_game': best_game,
        'worst_game': worst_game,
        'best_hero' : best_hero,
        'best_hero_winrate': best_hero_winrate,
        'most_played_hero': most_played_hero,
        'lane_roles': lane_roles   
    }

def format_duration(seconds):
    try:
        seconds = int(seconds)
        minutes = seconds // 60
        seconds  = seconds % 60
        return f'{minutes}:{seconds:02d}'
    except(ValueError, TypeError):
        return '0:00'

def format_number(value):
    try:
        if isinstance(value,float):
            return f'{value:.0f}' if value == int(value) else f'{value:.1f}'
        return str(value)
    except:
        return '0'
def get_lane_role_name(role_id):
    roles = {
        1: 'Carry',
        2: 'Midlaner',
        3: 'Offlaner',
        4: 'Support',
        5: 'Full Support'
    }
    return roles.get(role_id, 'Неизвестно')

@bot.message_handler(commands=['start','help'])
def send_welcome(message):
    bot.reply_to(message,
                 'Dota 2 Statistics Bot \n\n'
                 'Отправь мне Steam ID для получения статистики за последние матчи')
@bot.message_handler(func=lambda message:True)
def send_stats(message):
    steam_id = message.text.strip()
    
    if steam_id.startswith('/'):
        return
    bot.send_chat_action(message.chat.id,'typing')
    account_id = get_account_id(steam_id)
    if not account_id:
        bot.reply_to(message, 'Неверный Steam ID')
        return
    player_info = get_info_player(account_id)
    if not player_info:
        bot.reply_to(message, 'Не удалось получить информацию о игроке')
        return
    player_name = 'Неизвестно'
    if player_info and 'profile' in player_info:
        profile = player_info['profile']
        player_name = profile.get('personaname', 'Неизвестно')
    bot.send_message(message.chat.id, f'Собираю статистику для {player_name}')
    stats = analyz_matches(account_id)
    if not stats:
        bot.reply_to(message,' Не удалось собрать статистику с игрока, скорее всего профиль скрыт')
        return
    
    best_hero_name = heroes_dict.get(stats['best_hero'], 'Неизвестно') if stats['best_hero'] else 'Недостаточно данных'
    most_played_hero_id = stats['most_played_hero'][0] if stats['most_played_hero'] else None
    most_played_hero_name = heroes_dict.get(most_played_hero_id,'Неизвестно') if most_played_hero_id else 'Неизвестно'
    most_played_games = stats['most_played_hero'][1]['games'] if stats['most_played_hero'] else 0
    
    main_role_id = max(stats['lane_roles'].items(), key=lambda x: x[1])[0] if stats['lane_roles'] else 0
    main_role = get_lane_role_name(main_role_id)
    result = (
        f"👤 Игрок: {player_name}\n"
        f"📊 Статистика за последние {stats['total_matches']} матчей\n\n"
        
        f"🏆 Общая статистика:\n"
        f"   Победы: {stats['wins']}/{stats['total_matches']} ({stats['win_rate']:.1f}%)\n"
        f"   K/D/A: {format_number(stats['avg_kills'])}/{format_number(stats['avg_deaths'])}/{format_number(stats['avg_assists'])}\n"
        f"   KDA Ratio: {stats['kda_ratio']:.2f}\n"
        f"   Средний GPM: {format_number(stats['avg_gpm'])}\n"
        f"   Средний XPM: {format_number(stats['avg_xpm'])}\n"
        f"   Средний урон: {format_number(stats['avg_hero_damage'])}\n"
        f"   Средние ластхиты: {format_number(stats['avg_last_hits'])}\n"
        f"   Средняя длительность: {format_duration(stats['avg_duration'])}\n\n"
        
        f"🎮 Лучшая игра:\n"
        f"   Герой: {heroes_dict.get(stats['best_game'].get('hero_id'), 'Неизвестно')}\n"
        f"   K/D/A: {stats['best_game'].get('kills', 0)}/{stats['best_game'].get('deaths', 0)}/{stats['best_game'].get('assists', 0)}\n"
        f"   GPM: {stats['best_game'].get('gold_per_min', 0)} | XPM: {stats['best_game'].get('xp_per_min', 0)}\n"
        f"   Урон: {stats['best_game'].get('hero_damage', 0)}\n"
        f"   Ластхиты: {stats['best_game'].get('last_hits', 0)}\n"
        f"   Длительность: {format_duration(stats['best_game'].get('duration', 0))}\n\n"
        
        f"💀 Худшая игра:\n"
        f"   Герой: {heroes_dict.get(stats['worst_game'].get('hero_id'), 'Неизвестно')}\n"
        f"   K/D/A: {stats['worst_game'].get('kills', 0)}/{stats['worst_game'].get('deaths', 0)}/{stats['worst_game'].get('assists', 0)}\n"
        f"   GPM: {stats['worst_game'].get('gold_per_min', 0)} | XPM: {stats['worst_game'].get('xp_per_min', 0)}\n"
        f"   Урон: {stats['worst_game'].get('hero_damage', 0)}\n"
        f"   Ластхиты: {stats['worst_game'].get('last_hits', 0)}\n"
        f"   Длительность: {format_duration(stats['worst_game'].get('duration', 0))}\n\n"
        
        f"❤️ Герои:\n"
        f"   Лучший герой: {best_hero_name} ({stats['best_hero_winrate']:.1f}% винрейт)\n"
        f"   Самый популярный: {most_played_hero_name} ({most_played_games} игр)\n\n"
        
        f"🎯 Основная роль: {main_role}\n\n"
        
        f"🔗 Профиль OpenDota: https://www.opendota.com/players/{account_id}"
    )
    bot.send_message(message.chat.id, result)
    
if __name__ == '__main__':
    print('Bot is working')
    try:
        bot.polling(non_stop=True)
    except Exception as e:
        print(f'Error: {e}')
        