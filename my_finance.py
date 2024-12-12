import sqlite3
import traceback

import telebot
from telebot import types
import re
from datetime import datetime, timedelta
import calendar

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

import matplotlib.pyplot as plt
import matplotlib
import seaborn as sns
from statsmodels.tsa.holtwinters import ExponentialSmoothing

matplotlib.use('Agg')  # Важно для работы на сервере без GUI
from io import BytesIO
import numpy as np
import pandas as pd
import os


# Инициализация бота
bot = telebot.TeleBot('7212810100:AAEUpcoq36V_A3oadUDQmRx4cpASnR1qfjE')


# Инициализация БД
def init_db():
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    try:
        # Создание таблицы для карт
        c.execute('''CREATE TABLE IF NOT EXISTS cards
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER,
                      card_name TEXT,
                      balance REAL)''')

        # Создание таблицы для категорий
        c.execute('''CREATE TABLE IF NOT EXISTS categories
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER,
                      category_name TEXT)''')

        # Создание таблицы для транзакций
        c.execute('''CREATE TABLE IF NOT EXISTS transactions
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER,
                      card_id INTEGER,
                      category TEXT,
                      amount REAL,
                      date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# Инициализация БД при запуске
init_db()


@bot.message_handler(func=lambda message: message.text == '💳 Добавить карту')
def button_add_card(message):
    add_card_command(message)

@bot.message_handler(func=lambda message: message.text == '📊 Мои карты')
def button_show_cards(message):
    show_cards(message)

@bot.message_handler(func=lambda message: message.text == '➕ Добавить категорию')
def button_add_category(message):
    add_category_command(message)

@bot.message_handler(func=lambda message: message.text == '📋 Мои категории')
def button_show_categories(message):
    show_categories(message)

# Функции для работы с БД
def add_card(user_id, card_name, initial_balance):
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    try:
        c.execute('INSERT INTO cards (user_id, card_name, balance) VALUES (?, ?, ?)',
                  (user_id, card_name, initial_balance))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_cards(user_id):
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    try:
        c.execute('SELECT card_name, balance FROM cards WHERE user_id = ?', (user_id,))
        cards = c.fetchall()
        return cards
    except Exception as e:
        raise e
    finally:
        conn.close()


def add_category(user_id, category_name):
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    try:
        c.execute('INSERT INTO categories (user_id, category_name) VALUES (?, ?)',
                  (user_id, category_name))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_categories(user_id):
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    try:
        c.execute('SELECT category_name FROM categories WHERE user_id = ?', (user_id,))
        categories = [row[0] for row in c.fetchall()]
        return categories
    except Exception as e:
        raise e
    finally:
        conn.close()

def update_balance(user_id, card_name, amount):
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    try:
        c.execute('''UPDATE cards SET balance = balance + ? 
                     WHERE user_id = ? AND card_name = ?''',
                  (amount, user_id, card_name))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def delete_card(user_id, card_name):
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    try:
        c.execute('DELETE FROM cards WHERE user_id = ? AND card_name = ?',
                  (user_id, card_name))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def delete_category(user_id, category_name):
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    try:
        c.execute('DELETE FROM categories WHERE user_id = ? AND category_name = ?',
                  (user_id, category_name))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# Добавляем новую таблицу для хранения дат зарплаты
def init_salary_table():
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS salary_dates
                     (user_id INTEGER PRIMARY KEY,
                      first_date INTEGER,
                      second_date INTEGER)''')
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# Инициализация таблицы при запуске
init_salary_table()

# Обработчики команд
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton('💳 Добавить карту'),
        types.KeyboardButton('📊 Мои карты'),
        types.KeyboardButton('➕ Добавить категорию'),
        types.KeyboardButton('📋 Мои категории'),
        types.KeyboardButton('📈 Статистика'),
        types.KeyboardButton('💰 Дни до ЗП'),
        types.KeyboardButton('📋 История операций'),
        types.KeyboardButton('✏️ Изменить баланс карт')  # Новая кнопка
    )
    bot.reply_to(message,
                 "👋 *Привет! Я бот для учёта финансов*\n\n"
                 "🔥 *Основные возможности:*\n"
                 "• 💰 Учет доходов и расходов\n"
                 "• 💳 Управление несколькими картами\n"
                 "• 📊 Категоризация трат\n"
                 "• 📈 Детальная статистика\n"
                 "• 📱 Ежедневные отчеты\n"
                 "• 🎯 Прогноз баланса до зарплаты\n"
                 "• 📑 Экспорт данных в Excel\n\n"
                 "💡 *Как пользоваться:*\n"
                 "• Добавьте карты и категории расходов\n"
                 "• Записывайте расходы: введите сумму\n"
                 "• Записывайте доходы: введите +сумма категория\n"
                 "• Следите за статистикой\n\n"
                 "⚡️ *Команды для управления:*\n"
                 "📍 /start - главное меню\n"
                 "💳 /addcard - добавить карту\n"
                 "📋 /cards - список карт\n"
                 "➕ /addcategory - добавить категорию\n"
                 "📁 /categories - список категорий\n"
                 "📊 /stats - статистика расходов\n"
                 "💰 /salary - установить даты зарплаты\n"
                 "📈 /mystats - финансовая статистика\n"
                 "📝 /history - история операций\n"
                 "❌ /del\\_last - удалить последнюю транзакцию\n"
                 "📥 /export - выгрузка в excel файл\n"
                 "📈 /charts - графики\n"
                 "✏️ /editbalance - изменить баланс карты",
                 reply_markup=markup,
                 parse_mode='Markdown')


@bot.message_handler(func=lambda message: message.text == '✏️ Изменить баланс карт')
def edit_balance_button(message):
    edit_balance_command(message)

@bot.message_handler(func=lambda message: message.text == '💰 Дни до ЗП')
def salary_stats_button(message):
    show_salary_stats(message)


def get_stats_by_card(user_id, period_days, card_name=None):
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()

    date_from = datetime.now() - timedelta(days=period_days)

    if card_name:
        # Статистика для конкретной карты
        c.execute('''
            SELECT t.category, SUM(ABS(t.amount)) as total
            FROM transactions t
            JOIN cards c ON t.card_id = c.id
            WHERE t.user_id = ? 
            AND t.date >= ?
            AND t.amount < 0
            AND c.card_name = ?
            GROUP BY t.category
            ORDER BY total DESC
        ''', (user_id, date_from, card_name))

        category_stats = c.fetchall()

        c.execute('''
            SELECT SUM(ABS(t.amount))
            FROM transactions t
            JOIN cards c ON t.card_id = c.id
            WHERE t.user_id = ? 
            AND t.date >= ?
            AND t.amount < 0
            AND c.card_name = ?
        ''', (user_id, date_from, card_name))
    else:
        # Статистика по всем картам
        c.execute('''
            SELECT c.card_name, SUM(ABS(t.amount)) as total
            FROM transactions t
            JOIN cards c ON t.card_id = c.id
            WHERE t.user_id = ? 
            AND t.date >= ?
            AND t.amount < 0
            GROUP BY c.card_name
            ORDER BY total DESC
        ''', (user_id, date_from))

        category_stats = c.fetchall()

        c.execute('''
            SELECT SUM(ABS(t.amount))
            FROM transactions t
            WHERE t.user_id = ? 
            AND t.date >= ?
            AND t.amount < 0
        ''', (user_id, date_from))

    total_spent = c.fetchone()[0] or 0
    conn.close()

    return category_stats, total_spent


def set_salary_dates(user_id, first_date, second_date):
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    try:
        c.execute('''INSERT OR REPLACE INTO salary_dates (user_id, first_date, second_date)
                     VALUES (?, ?, ?)''', (user_id, first_date, second_date))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_salary_dates(user_id):
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    try:
        c.execute('SELECT first_date, second_date FROM salary_dates WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        return result if result else None
    except Exception as e:
        raise e
    finally:
        conn.close()


def get_next_salary_date(salary_date):
    today = datetime.now()
    current_year = today.year
    current_month = today.month

    # Создаем дату зарплаты для текущего месяца
    try:
        salary = datetime(current_year, current_month, salary_date)
    except ValueError:
        # Если указано например 31 число, а в месяце меньше дней
        salary = datetime(current_year, current_month, calendar.monthrange(current_year, current_month)[1])

    # Если дата уже прошла, берем следующий месяц
    if salary < today:
        if current_month == 12:
            salary = datetime(current_year + 1, 1, salary_date)
        else:
            try:
                salary = datetime(current_year, current_month + 1, salary_date)
            except ValueError:
                salary = datetime(current_year, current_month + 1,
                                  calendar.monthrange(current_year, current_month + 1)[1])

    # Проверяем на выходные
    while salary.weekday() in [5, 6]:  # 5 - суббота, 6 - воскресенье
        salary = salary - timedelta(days=1)

    return salary


@bot.message_handler(commands=['salary'])
def set_salary_command(message):
    msg = bot.reply_to(message,
                       "Укажите два числа месяца когда вы получаете зарплату через пробел (например: 14 29):")
    bot.register_next_step_handler(msg, process_salary_dates)


def process_salary_dates(message):
    try:
        first_date, second_date = map(int, message.text.split())
        if 1 <= first_date <= 31 and 1 <= second_date <= 31:
            set_salary_dates(message.from_user.id, first_date, second_date)
            bot.reply_to(message, "✅ Даты зарплаты успешно установлены!")
            show_salary_stats(message)
        else:
            bot.reply_to(message, "❌ Числа должны быть от 1 до 31")
    except ValueError:
        bot.reply_to(message, "❌ Неверный формат. Укажите два числа через пробел")


@bot.message_handler(commands=['mystats'])
def show_salary_stats(message):
    salary_dates = get_salary_dates(message.from_user.id)
    if not salary_dates:
        bot.reply_to(message,
                     "⚠️ Даты зарплаты не установлены. Используйте /salary чтобы установить")
        return

    first_date, second_date = salary_dates

    # Определяем следующую дату зарплаты
    next_first = get_next_salary_date(first_date)
    next_second = get_next_salary_date(second_date)
    next_salary = min(next_first, next_second)

    # Получаем общий баланс по всем картам
    total_balance = 0
    cards = get_cards(message.from_user.id)
    for _, balance in cards:
        total_balance += balance

    # Рассчитываем дни до зарплаты
    days_until_salary = (next_salary - datetime.now()).days + 1

    # Рассчитываем дневной бюджет
    daily_budget = total_balance / days_until_salary if days_until_salary > 0 else 0

    # Получаем средний расход за последние 30 дней
    _, avg_spending = get_stats_by_card(message.from_user.id, 30)
    avg_daily_spending = avg_spending / 30 if avg_spending else 0

    response = "📊 *Финансовая статистика:*\n\n"
    response += f"💰 Текущий баланс: *{total_balance}* ₽\n"
    response += f"📅 Дней до зарплаты: *{days_until_salary}*\n"
    response += f"💵 Можно тратить в день: *{daily_budget:.2f}* ₽\n\n"

    response += "📈 *Дополнительная информация:*\n"
    response += f"📊 Средний расход в день: *{avg_daily_spending:.2f}* ₽\n"

    # Анализ трат
    if daily_budget > 0:
        if avg_daily_spending > daily_budget:
            response += "\n⚠️ *Внимание!* Ваши средние траты превышают рекомендуемый дневной бюджет!"
        elif avg_daily_spending < daily_budget * 0.7:
            response += "\n✅ Отлично! Ваши траты ниже дневного бюджета!"

    # Следующая зарплата
    weekdays = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']
    response += f"\n\n📅 Следующая зарплата: *{next_salary.strftime('%d.%m.%Y')}* " + \
                f"({weekdays[next_salary.weekday()]})"

    bot.reply_to(message, response, parse_mode='Markdown')


def create_heatmap(user_id):
    plt.clf()
    plt.style.use('default')

    df = get_user_transactions(user_id)
    df['date'] = pd.to_datetime(df['date'])

    # Добавляем день недели и час
    df['weekday'] = df['date'].dt.day_name()
    df['hour'] = df['date'].dt.hour

    # Определяем периоды дня
    def get_period(hour):
        if 6 <= hour < 12:
            return 'Утро'
        elif 12 <= hour < 18:
            return 'День'
        elif 18 <= hour < 23:
            return 'Вечер'
        else:
            return 'Ночь'

    # Берем только расходы
    spending_df = df[df['amount'] < 0].copy()
    spending_df['amount'] = spending_df['amount'].abs()
    spending_df['period'] = spending_df['hour'].apply(get_period)

    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    weekdays_ru = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
    hours = list(range(24))

    heatmap_data = pd.DataFrame(0, index=weekdays, columns=hours)

    for _, row in spending_df.iterrows():
        heatmap_data.at[row['weekday'], row['hour']] += row['amount']

    # Нормализация данных для лучшей визуализации
    normalized_data = (heatmap_data - heatmap_data.min().min()) / (heatmap_data.max().max() - heatmap_data.min().min())

    # Создаем график
    fig = plt.figure(figsize=(16, 12))

    # Основная тепловая карта
    ax1 = plt.subplot2grid((3, 2), (0, 0), colspan=2, rowspan=2)
    im = ax1.imshow(normalized_data,
                    cmap='RdYlBu_r',
                    aspect='auto',
                    interpolation='nearest')

    # Настройка осей
    ax1.set_xticks(np.arange(24))
    ax1.set_yticks(np.arange(7))
    ax1.set_xticklabels([f'{i}:00' for i in hours], rotation=45, ha='right')
    ax1.set_yticklabels(weekdays_ru)

    # Добавляем значения в ячейки
    for i in range(len(weekdays)):
        for j in range(24):
            value = heatmap_data.iloc[i, j]
            if value > 0:
                text = ax1.text(j, i, f'{value:,.0f}₽',
                                ha="center", va="center",
                                color="black" if normalized_data.iloc[i, j] < 0.5 else "white",
                                fontsize=8,
                                fontweight='bold')

    # Цветовая шкала
    cbar = plt.colorbar(im, ax=ax1, pad=0.02)
    cbar.set_label('Интенсивность расходов', rotation=270, labelpad=15)

    # График по периодам дня
    ax2 = plt.subplot2grid((3, 2), (2, 0))
    period_data = spending_df.groupby('period')['amount'].sum()
    periods = ['Утро', 'День', 'Вечер', 'Ночь']
    period_data = period_data.reindex(periods)
    ax2.bar(periods, period_data.values, color='skyblue')
    ax2.set_title('Расходы по времени суток')
    ax2.set_ylabel('Сумма (₽)')

    # Добавляем подписи значений
    for i, v in enumerate(period_data.values):
        ax2.text(i, v, f'{v:,.0f}₽', ha='center', va='bottom')

    # График по дням недели
    ax3 = plt.subplot2grid((3, 2), (2, 1))
    weekly_data = spending_df.groupby('weekday')['amount'].sum()
    weekly_data = weekly_data.reindex(weekdays)
    ax3.bar(weekdays_ru, weekly_data.values, color='lightcoral')
    ax3.set_title('Расходы по дням недели')
    ax3.set_ylabel('Сумма (₽)')
    plt.xticks(rotation=45, ha='right')

    # Добавляем подписи значений
    for i, v in enumerate(weekly_data.values):
        ax3.text(i, v, f'{v:,.0f}₽', ha='center', va='bottom')

    # Статистика
    max_hour = heatmap_data.sum().idxmax()
    max_day = weekdays_ru[weekdays.index(heatmap_data.sum(axis=1).idxmax())]
    max_period = period_data.idxmax()

    stats_text = (
        f'🔥 Пиковые траты: {heatmap_data.values.max():,.0f}₽\n'
        f'⏰ Активное время: {max_hour}:00-{max_hour + 1}:00\n'
        f'📅 Активный день: {max_day}\n'
        f'⌚ Активный период: {max_period}\n'
        f'💰 Средний расход: {heatmap_data.mean().mean():,.0f}₽\n'
        f'📊 Всего операций: {len(spending_df)}'
    )

    plt.figtext(1.02, 0.7, stats_text,
                bbox=dict(facecolor='white',
                          edgecolor='gray',
                          alpha=0.9,
                          boxstyle='round,pad=0.5'),
                fontsize=10)

    plt.suptitle('Анализ расходов по времени',
                 size=16,
                 fontweight='bold',
                 y=0.95)

    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=300)
    buf.seek(0)
    plt.close()
    return buf


@bot.message_handler(commands=['heatmap'])
def show_heatmap(message):
    user_id = message.from_user.id
    buf = create_heatmap(user_id)
    bot.send_photo(message.chat.id, buf)

def get_last_transactions(user_id, limit=15):
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute('''
        SELECT 
            t.date,
            c.card_name,
            t.category,
            t.amount
        FROM transactions t
        JOIN cards c ON t.card_id = c.id
        WHERE t.user_id = ?
        ORDER BY t.date DESC
        LIMIT ?
    ''', (user_id, limit))
    transactions = c.fetchall()
    conn.close()
    return transactions


def delete_last_transaction(user_id):
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    try:
        # Получаем последнюю транзакцию со всеми деталями
        c.execute('''
            SELECT t.id, t.card_id, t.amount, t.category, c.card_name 
            FROM transactions t
            JOIN cards c ON t.card_id = c.id
            WHERE t.user_id = ? 
            ORDER BY t.date DESC, t.id DESC 
            LIMIT 1
        ''', (user_id,))

        transaction = c.fetchone()
        if not transaction:
            return "🤷‍♂️ Транзакций больше нет"

        transaction_id, card_id, amount, category, card_name = transaction

        # Возвращаем деньги на карту
        c.execute('''
            UPDATE cards 
            SET balance = balance - ? 
            WHERE id = ?
        ''', (amount, card_id))

        # Получаем новый баланс
        c.execute('SELECT balance FROM cards WHERE id = ?', (card_id,))
        new_balance = c.fetchone()[0]

        # Удаляем транзакцию
        c.execute('DELETE FROM transactions WHERE id = ?', (transaction_id,))

        conn.commit()

        return (f"✅ Транзакция успешно удалена!\n\n"
                f"💳 Карта: {card_name}\n"
                f"📋 Категория: {category}\n"
                f"💰 Сумма: {abs(amount)} ₽\n"
                f"💵 Новый баланс: {new_balance} ₽")

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


@bot.message_handler(commands=['del_last'])
def handle_del_last(message):
    user_id = message.from_user.id
    result = delete_last_transaction(user_id)
    bot.reply_to(message, result)

@bot.message_handler(commands=['history'])
@bot.message_handler(func=lambda message: message.text == '📋 История операций')
def show_transaction_history(message):
    transactions = get_last_transactions(message.from_user.id)

    if not transactions:
        bot.reply_to(message, "У вас пока нет операций")
        return

    response = "📋 *Последние операции:*\n\n"
    for date, card, category, amount in transactions:
        trans_date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
        formatted_date = trans_date.strftime('%d.%m.%Y %H:%M')

        emoji = '➖' if amount < 0 else '➕'

        # Экранируем специальные символы для Markdown
        safe_card = card.replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
        safe_category = category.replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')

        response += f"{emoji} {formatted_date}\n"
        response += f"💳 Карта: *{safe_card}*\n"
        response += f"📁 Категория: {safe_category}\n"
        response += f"💰 Сумма: *{abs(amount)}* ₽\n"
        response += "─────────────────\n"

    try:
        bot.reply_to(message, response, parse_mode='Markdown')
    except:
        # Если всё же возникает ошибка, отправляем без форматирования
        bot.reply_to(message, response.replace('*', ''))

@bot.message_handler(commands=['stats'])
@bot.message_handler(func=lambda message: message.text == '📈 Статистика')
def show_stats_menu(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("📊 Все карты", callback_data="stats_type_all"),
        types.InlineKeyboardButton("💳 Выбрать карту", callback_data="stats_type_card")
    )
    bot.reply_to(message, "Выберите тип статистики:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('stats_type_'))
def select_stats_type(call):
    stats_type = call.data.split('_')[2]

    if stats_type == 'all':
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("За день", callback_data="stats_all_1"),
            types.InlineKeyboardButton("За неделю", callback_data="stats_all_7"),
            types.InlineKeyboardButton("За месяц", callback_data="stats_all_30")
        )
        bot.edit_message_text(
            "📊 Выберите период для общей статистики:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    else:
        cards = get_cards(call.from_user.id)
        if not cards:
            bot.edit_message_text(
                "У вас пока нет добавленных карт",
                call.message.chat.id,
                call.message.message_id
            )
            return

        markup = types.InlineKeyboardMarkup()
        for card_name, _ in cards:
            markup.add(types.InlineKeyboardButton(
                card_name, callback_data=f"stats_card_{card_name}"))

        bot.edit_message_text(
            "💳 Выберите карту для просмотра статистики:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith('stats_card_'))
def select_card_period(call):
    card_name = call.data.replace('stats_card_', '')
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("За день", callback_data=f"stats_period_{card_name}_1"),
        types.InlineKeyboardButton("За неделю", callback_data=f"stats_period_{card_name}_7"),
        types.InlineKeyboardButton("За месяц", callback_data=f"stats_period_{card_name}_30")
    )
    bot.edit_message_text(
        f"📅 Выберите период для карты {card_name}:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith(('stats_all_', 'stats_period_')))
def show_stats_result(call):
    if call.data.startswith('stats_all_'):
        _, _, days = call.data.split('_')
        days = int(days)
        card_name = None
    else:
        _, _, card_name, days = call.data.split('_')
        days = int(days)

    period_names = {1: "день", 7: "неделю", 30: "месяц"}

    stats, total_spent = get_stats_by_card(call.from_user.id, days, card_name)

    if not total_spent:
        response = f"За этот {period_names[days]} расходов не было"
    else:
        if card_name:
            response = f"📊 Статистика по карте *{card_name}* за {period_names[days]}:\n\n"
        else:
            response = f"📊 Общая статистика за {period_names[days]}:\n\n"

        response += f"💰 Общая сумма расходов: *{total_spent}* ₽\n\n"

        if card_name:
            response += "По категориям:\n"
        else:
            response += "По картам:\n"

        for name, amount in stats:
            percentage = (amount / total_spent) * 100
            response += f"• {name}: *{amount}* ₽ ({percentage:.1f}%)\n"

    bot.edit_message_text(
        response,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown'
    )
# Обработчик для чисел
@bot.message_handler(func=lambda message: message.text.replace(',', '').replace('.', '').isdigit())
def handle_amount(message):
    # Заменяем запятую на точку для корректной конвертации в float
    amount = float(message.text.replace(',', '.'))
    cards = get_cards(message.from_user.id)

    if not cards:
        bot.reply_to(message, "У вас пока нет добавленных карт")
        return

    # Сохраняем сумму во временный словарь
    user_data = {}
    user_data[message.from_user.id] = {'amount': amount}

    # Создаем клавиатуру с картами
    markup = types.InlineKeyboardMarkup()
    for card_name, _ in cards:
        markup.add(types.InlineKeyboardButton(
            card_name, callback_data=f"select_card_{card_name}_{amount}"))

    bot.reply_to(message,
                 f"💳 Выберите карту для списания *{amount}* ₽:",
                 reply_markup=markup,
                 parse_mode='Markdown')


@bot.callback_query_handler(func=lambda call: call.data.startswith('select_card_'))
def process_card_selection(call):
    _, _, card_name, amount = call.data.split('_')
    amount = float(amount)

    # Получаем категории пользователя
    categories = get_categories(call.from_user.id)
    if not categories:
        bot.edit_message_text(
            "У вас пока нет категорий расходов. Добавьте их через команду /addcategory",
            call.message.chat.id,
            call.message.message_id
        )
        return

    # Создаем клавиатуру с категориями
    markup = types.InlineKeyboardMarkup()
    for category in categories:
        markup.add(types.InlineKeyboardButton(
            category, callback_data=f"spend_{amount}_{category}_{card_name}"))

    bot.edit_message_text(
        f"📋 Выберите категорию расхода для суммы *{amount}* ₽:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['addcard'])
def add_card_command(message):
    msg = bot.reply_to(message, "Введите название карты и начальный баланс через пробел:")
    bot.register_next_step_handler(msg, process_add_card)


def process_add_card(message):
    try:
        card_name, initial_balance = message.text.split(maxsplit=1)
        if not card_name or len(card_name) > 50:  # Добавить проверку
            raise ValueError("Некорректное название карты")
        initial_balance = float(initial_balance)
        if initial_balance < 0:  # Добавить проверку
            raise ValueError("Баланс не может быть отрицательным")
        add_card(message.from_user.id, card_name, initial_balance)
        bot.reply_to(message, f"✅ Карта '{card_name}' добавлена с балансом *{initial_balance}* ₽",
                     parse_mode='Markdown')
    except ValueError as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")


@bot.message_handler(commands=['cards'])
def show_cards(message):
    cards = get_cards(message.from_user.id)
    if not cards:
        bot.reply_to(message, "У вас пока нет добавленных карт")
        return

    markup = types.InlineKeyboardMarkup()
    response = "💳 Ваши карты:\n\n"
    for card_name, balance in cards:
        response += f"*{card_name}*: *{balance:.2f}* ₽\n"
        markup.add(types.InlineKeyboardButton(f"❌ Удалить {card_name}", callback_data=f"del_card_{card_name}"))

    bot.reply_to(message, response, parse_mode='Markdown', reply_markup=markup)


@bot.message_handler(commands=['addcategory'])
def add_category_command(message):
    msg = bot.reply_to(message, "Введите название новой категории расходов:")
    bot.register_next_step_handler(msg, process_add_category)


def process_add_category(message):
    category_name = message.text.strip()
    add_category(message.from_user.id, category_name)
    bot.reply_to(message, f"✅ Категория '{category_name}' добавлена")


@bot.message_handler(commands=['categories'])
def show_categories(message):
    categories = get_categories(message.from_user.id)
    if not categories:
        bot.reply_to(message, "У вас пока нет добавленных категорий")
        return

    markup = types.InlineKeyboardMarkup()
    response = "📋 Ваши категории расходов:\n\n"
    for category in categories:
        response += f"• {category}\n"
        markup.add(types.InlineKeyboardButton(f"❌ Удалить {category}", callback_data=f"del_cat_{category}"))

    bot.reply_to(message, response, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('del_card_'))
def delete_card_callback(call):
    card_name = call.data.replace('del_card_', '')
    delete_card(call.from_user.id, card_name)
    bot.edit_message_text(
        f"✅ Карта *{card_name}* удалена",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('del_cat_'))
def delete_category_callback(call):
    category_name = call.data.replace('del_cat_', '')
    delete_category(call.from_user.id, category_name)
    bot.edit_message_text(
        f"✅ Категория *{category_name}* удалена",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown'
    )


@bot.message_handler(commands=['editbalance'])
def edit_balance_command(message):
    cards = get_cards(message.from_user.id)
    if not cards:
        bot.reply_to(message, "У вас пока нет добавленных карт")
        return

    markup = types.InlineKeyboardMarkup()
    for card_name, _ in cards:
        markup.add(types.InlineKeyboardButton(
            card_name, callback_data=f"edit_{card_name}"))

    bot.reply_to(message, "Выберите карту для изменения баланса:",
                 reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('edit_'))
def edit_balance_callback(call):
    card_name = call.data.replace('edit_', '')
    msg = bot.send_message(call.message.chat.id,
                           f"Введите новый баланс для карты '{card_name}':")
    bot.register_next_step_handler(msg, process_edit_balance, card_name)


def process_edit_balance(message, card_name):
    try:
        new_balance = float(message.text)
        conn = sqlite3.connect('finance.db')
        c = conn.cursor()
        c.execute('''UPDATE cards SET balance = ? 
                     WHERE user_id = ? AND card_name = ?''',
                  (new_balance, message.from_user.id, card_name))
        conn.commit()
        conn.close()
        bot.reply_to(message,
                     f"✅ Баланс карты '{card_name}' обновлен: *{new_balance}* ₽",
                     parse_mode='Markdown')
    except ValueError:
        bot.reply_to(message, "❌ Неверный формат суммы")


# Обработка расходов
@bot.message_handler(func=lambda message: re.match(r'^\d+(\.\d+)?\s+\w+', message.text))
def handle_expense(message):
    try:
        amount, category = message.text.split(maxsplit=1)
        amount = float(amount)

        cards = get_cards(message.from_user.id)
        if not cards:
            bot.reply_to(message, "У вас пока нет добавленных карт")
            return

        markup = types.InlineKeyboardMarkup()
        for card_name, _ in cards:
            markup.add(types.InlineKeyboardButton(
                card_name, callback_data=f"spend_{amount}_{category}_{card_name}"))

        bot.reply_to(message,
                     f"Выберите карту для списания *{amount}* ₽ (категория: {category}):",
                     reply_markup=markup,
                     parse_mode='Markdown')
    except ValueError:
        bot.reply_to(message, "❌ Неверный формат. Используйте: Сумма Категория")


@bot.callback_query_handler(func=lambda call: call.data.startswith('spend_'))
def process_expense(call):
    _, amount, category, card_name = call.data.split('_')
    amount = float(amount)

    update_balance(call.from_user.id, card_name, -amount)

    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute('SELECT balance FROM cards WHERE user_id = ? AND card_name = ?',
              (call.from_user.id, card_name))
    current_balance = c.fetchone()[0]

    c.execute('''INSERT INTO transactions (user_id, card_id, category, amount)
                 SELECT ?, cards.id, ?, ?
                 FROM cards
                 WHERE cards.user_id = ? AND cards.card_name = ?''',
              (call.from_user.id, category, -amount, call.from_user.id, card_name))
    conn.commit()
    conn.close()

    bot.edit_message_text(
        f"✅ Расход записан:\n"
        f"Карта: *{card_name}*\n"
        f"Сумма: *{amount:.2f}* ₽\n"
        f"Категория: {category}\n"
        f"💰 Текущий баланс: *{current_balance:.2f}* ₽",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown'
    )


@bot.message_handler(func=lambda message: message.text.startswith('+') and ' ' in message.text)
def handle_income(message):
    try:
        # Разбираем сообщение на сумму и категорию
        parts = message.text[1:].split(maxsplit=1)  # Убираем '+' и разделяем
        if len(parts) != 2:
            bot.reply_to(message, "📝 Формат: +сумма категория\nНапример: +500 зарплата")
            return

        amount = float(parts[0])
        category = parts[1]

        # Получаем список карт пользователя
        cards = get_cards(message.from_user.id)
        if not cards:
            bot.reply_to(message, "💳 У вас пока нет добавленных карт")
            return

        # Создаем клавиатуру с картами
        markup = types.InlineKeyboardMarkup()
        for card_name, _ in cards:
            markup.add(types.InlineKeyboardButton(
                card_name,
                callback_data=f"income_{amount}_{category}_{card_name}"
            ))

        bot.reply_to(
            message,
            f"💰 Выберите карту для зачисления *{amount}* ₽\n📝 Категория: _{category}_",
            reply_markup=markup,
            parse_mode='Markdown'
        )

    except ValueError:
        bot.reply_to(message, "❗️ Неверный формат суммы")


@bot.callback_query_handler(func=lambda call: call.data.startswith('income_'))
def process_income(call):
    _, amount, category, card_name = call.data.split('_')
    amount = float(amount)

    # Обновляем баланс карты
    update_balance(call.from_user.id, card_name, amount)

    # Записываем транзакцию
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()

    # Получаем обновленный баланс
    c.execute('SELECT balance FROM cards WHERE user_id = ? AND card_name = ?',
              (call.from_user.id, card_name))
    current_balance = c.fetchone()[0]

    # Добавляем транзакцию
    c.execute('''INSERT INTO transactions (user_id, card_id, category, amount, date)
                 SELECT ?, cards.id, ?, ?, datetime('now')
                 FROM cards
                 WHERE cards.user_id = ? AND cards.card_name = ?''',
              (call.from_user.id, category, amount, call.from_user.id, card_name))

    conn.commit()
    conn.close()

    # Отправляем подтверждение
    bot.edit_message_text(
        f"✅ Доход записан:\n"
        f"💳 Карта: *{card_name}*\n"
        f"💰 Сумма: *+{amount:.2f}* ₽\n"
        f"📝 Категория: _{category}_\n"
        f"💵 Текущий баланс: *{current_balance:.2f}* ₽",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['charts'])
def show_charts_menu(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("📊 Расходы по категориям", callback_data="pie_category"),
        types.InlineKeyboardButton("📈 Динамика трат", callback_data="line_spending"),
        types.InlineKeyboardButton("📊 Сравнение месяцев", callback_data="bar_months"),
        types.InlineKeyboardButton("🔄 Доходы vs Расходы", callback_data="compare_income")
    )
    bot.reply_to(message, "Выберите тип графика:", reply_markup=markup)
@bot.callback_query_handler(func=lambda call: call.data.startswith(('pie_', 'line_', 'bar_', 'compare_')))
def handle_chart_selection(call):
    user_id = call.from_user.id
    chart_type = call.data

    if chart_type == 'pie_category':
        buf = create_category_pie(user_id)
        bot.send_photo(call.message.chat.id, buf)

    elif chart_type == 'line_spending':
        buf = create_spending_line(user_id)
        bot.send_photo(call.message.chat.id, buf)

    elif chart_type == 'bar_months':
        buf = create_monthly_bar(user_id)
        bot.send_photo(call.message.chat.id, buf)

    elif chart_type == 'compare_income':
        buf = create_income_comparison(user_id)
        bot.send_photo(call.message.chat.id, buf)


def get_user_transactions(user_id):
    conn = sqlite3.connect('finance.db')
    query = '''
    SELECT 
        t.*,
        c.card_name,
        CASE 
            WHEN t.amount < 0 THEN 'Расход'
            ELSE 'Пополнение'
        END as type
    FROM transactions t
    JOIN cards c ON t.card_id = c.id
    WHERE t.user_id = ?
    '''
    df = pd.read_sql_query(query, conn, params=(user_id,))
    conn.close()
    df['date'] = pd.to_datetime(df['date'])
    return df


def calculate_days_until_salary(current_day, first_date, second_date):
    """Рассчитывает количество дней до следующей зарплаты"""
    today = datetime.now()
    current_month = today.month
    current_year = today.year

    # Создаем даты зарплаты для текущего месяца
    first_salary = datetime(current_year, current_month, first_date)
    second_salary = datetime(current_year, current_month, second_date)

    # Если обе даты зарплаты уже прошли в этом месяце, смотрим на следующий месяц
    if today > second_salary:
        if current_month == 12:
            next_month = 1
            next_year = current_year + 1
        else:
            next_month = current_month + 1
            next_year = current_year

        first_salary = datetime(next_year, next_month, first_date)
        return (first_salary - today).days

    # Если первая дата зарплаты прошла, но вторая - нет
    if today > first_salary and today <= second_salary:
        return (second_salary - today).days

    # Если обе даты впереди, возвращаем дни до ближайшей
    return (first_salary - today).days

def get_safety_indicator(safety_index):
    if safety_index >= 75:
        return "🟢"
    elif safety_index >= 50:
        return "🟡"
    elif safety_index >= 25:
        return "🟠"
    elif safety_index >= 0:
        return "🔴"
    else:
        return "⛔️"

def get_safety_description(safety_index):
    if safety_index >= 75:
        return "Отличный запас"
    elif safety_index >= 50:
        return "Хороший запас"
    elif safety_index >= 25:
        return "Умеренный риск"
    elif safety_index >= 0:
        return "Высокий риск"
    else:
        return "Критический риск"

@bot.message_handler(func=lambda message: message.text.lower().startswith('прогноз'))
def forecast_spending(message):
    try:
        amount = float(message.text.split()[1])
        user_id = message.from_user.id

        markup = types.InlineKeyboardMarkup(row_width=2)

        conn = sqlite3.connect('finance.db')
        c = conn.cursor()
        c.execute('SELECT card_name FROM cards WHERE user_id = ?', (user_id,))
        cards = c.fetchall()
        conn.close()

        buttons = []
        for card in cards:
            buttons.append(types.InlineKeyboardButton(
                f"💳 {card[0]}",
                callback_data=f"forecast_{amount}_{card[0]}"
            ))

        buttons.append(types.InlineKeyboardButton(
            "💰 По всем картам",
            callback_data=f"forecast_{amount}_all"
        ))

        markup.add(*buttons)

        bot.reply_to(message, "Выберите карту для прогноза:", reply_markup=markup)

    except (IndexError, ValueError):
        bot.reply_to(message, "❌ Используйте формат: прогноз [сумма]")


@bot.callback_query_handler(func=lambda call: call.data.startswith('forecast_'))
def process_forecast_callback(call):
    try:
        _, amount, card_choice = call.data.split('_', 2)
        amount = float(amount)
        user_id = call.from_user.id

        if card_choice == 'all':
            conn = sqlite3.connect('finance.db')
            c = conn.cursor()
            c.execute('SELECT SUM(balance) FROM cards WHERE user_id = ?', (user_id,))
            current_balance = c.fetchone()[0] or 0
            card_name = "все карты"
            conn.close()
        else:
            conn = sqlite3.connect('finance.db')
            c = conn.cursor()
            c.execute('SELECT balance FROM cards WHERE user_id = ? AND card_name = ?', (user_id, card_choice))
            current_balance = c.fetchone()[0] or 0
            card_name = card_choice
            conn.close()

        conn = sqlite3.connect('finance.db')
        c = conn.cursor()
        c.execute('SELECT first_date, second_date FROM salary_dates WHERE user_id = ?', (user_id,))
        salary_dates = c.fetchone()
        conn.close()

        if not salary_dates:
            bot.answer_callback_query(call.id, "❌ Сначала установите даты зарплаты командой /salary")
            return

        today = datetime.now().day
        first_date, second_date = salary_dates
        days_until_salary = calculate_days_until_salary(today, first_date, second_date)

        _, avg_spending = get_stats_by_card(user_id, 30)
        avg_daily_spending = avg_spending / 30 if avg_spending else 0

        balance_after_purchase = current_balance - amount

        if balance_after_purchase < 0:
            response = "🔮 *Прогноз влияния траты:*\n\n"
            response += f"💳 *Расчет для:* {card_name}\n"
            response += f"💰 Текущий баланс: *{current_balance:,.2f}* ₽\n"
            response += f"💳 Сумма покупки: *{amount:,.2f}* ₽\n"
            response += f"⏳ Дней до зарплаты: *{days_until_salary}*\n\n"

            response += "⛔️ *ВНИМАНИЕ:* Недостаточно средств!\n"
            response += f"• Не хватает: *{abs(balance_after_purchase):,.2f}* ₽\n"
            response += f"• Средний расход в день: *{avg_daily_spending:,.2f}* ₽\n\n"

            if days_until_salary <= 1:
                response += "💡 *Завтра зарплата!*\n\n"

            response += "🎯 *Рекомендация:* Покупка невозможна - недостаточно средств\n"
            response += f"🛡 *Статус:* ⛔️ Критический риск"

            response += f"\n\n📊 *Прогноз доступных средств:*\n"
            response += f"⛔️ Баланс будет отрицательным: *{balance_after_purchase:,.2f}* ₽"
        else:
            if days_until_salary <= 1:
                daily_budget = current_balance
                daily_budget_after = balance_after_purchase
                potential_savings = balance_after_purchase - avg_daily_spending
                risk_assessment = "✅ Покупка безопасна" if balance_after_purchase > avg_daily_spending * 2 else "⚠️ Учтите, что это последний день перед зарплатой"
            else:
                daily_budget = current_balance / days_until_salary
                daily_budget_after = balance_after_purchase / days_until_salary
                potential_savings = balance_after_purchase - (avg_daily_spending * days_until_salary)
                risk_assessment = analyze_risk(daily_budget_after, avg_daily_spending)

            safety_index = min(
                ((balance_after_purchase - (avg_daily_spending * days_until_salary)) /
                 (avg_daily_spending * days_until_salary)) * 100,
                100
            ) if avg_daily_spending > 0 and days_until_salary > 0 else 0

            safety_indicator = get_safety_indicator(safety_index)

            response = "🔮 *Прогноз влияния траты:*\n\n"
            response += f"💳 *Расчет для:* {card_name}\n"
            response += f"💰 Текущий баланс: *{current_balance:,.2f}* ₽\n"
            response += f"💳 Сумма покупки: *{amount:,.2f}* ₽\n"
            response += f"⏳ Дней до зарплаты: *{days_until_salary}*\n\n"

            response += "📊 *Анализ бюджета:*\n"
            if days_until_salary <= 1:
                response += f"• Остаток после покупки: *{balance_after_purchase:,.2f}* ₽\n"
                response += f"• Средний расход в день: *{avg_daily_spending:,.2f}* ₽\n"
                response += f"\n💡 *Завтра зарплата!*\n"
            else:
                response += f"• Текущий дневной бюджет: *{daily_budget:,.2f}* ₽/день\n"
                response += f"• Дневной бюджет после покупки: *{daily_budget_after:,.2f}* ₽/день\n"
                response += f"• Средний расход в день: *{avg_daily_spending:,.2f}* ₽\n"

            response += f"\n🎯 *Рекомендация:* {risk_assessment}\n"

            if potential_savings > 0:
                response += f"\n💰 *Потенциал накоплений до ЗП:* {potential_savings:,.2f}₽"

            response += f"\n🛡 *Индекс безопасности:* {safety_indicator} {safety_index:.0f}% - {get_safety_description(safety_index)}"

            response += "\n\n📊 *Прогноз доступных средств:*\n"
            response += f"• {datetime.now().strftime('%d.%m')}: {balance_after_purchase:.2f} ₽"

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=response,
            parse_mode='Markdown'
        )

    except Exception as e:
        print(f"Error in forecast: {str(e)}")
        traceback.print_exc()
        bot.answer_callback_query(call.id, "Произошла ошибка при расчете прогноза")

def analyze_risk(daily_budget, avg_daily_spending):
    if daily_budget >= avg_daily_spending * 1.5:
        return "✅ *Покупка безопасна*\nУ вас останется достаточный запас средств до зарплаты"
    elif daily_budget >= avg_daily_spending * 1.2:
        return "💚 *Покупка допустима*\nБюджет будет немного ограничен, но это некритично"
    elif daily_budget >= avg_daily_spending:
        return "⚠️ *Будьте осторожны*\nПридется более внимательно следить за тратами"
    elif daily_budget >= avg_daily_spending * 0.7:
        return "🔴 *Высокий риск*\nРекомендуется отложить покупку или найти дополнительный источник дохода"
    else:
        return "⛔️ *Критический риск*\nПокупка может привести к нехватке средств до зарплаты"

def create_category_pie(user_id):
    plt.clf()
    plt.style.use('default')

    df = get_user_transactions(user_id)
    df_expenses = df[df['amount'] < 0].copy()
    df_expenses['amount'] = df_expenses['amount'].abs()

    category_sums = df_expenses.groupby('category')['amount'].sum()
    category_sums = category_sums.sort_values(ascending=False)

    colors = plt.cm.Pastel1(np.linspace(0, 1, len(category_sums)))

    # Увеличиваем размер фигуры
    fig, ax = plt.subplots(figsize=(15, 10))

    wedges, texts, autotexts = ax.pie(category_sums,
                                      labels=[''] * len(category_sums),
                                      colors=colors,
                                      shadow=True,
                                      startangle=90,
                                      autopct='')

    # Создаем массив различных расстояний для текста
    distances = np.linspace(1.3, 2.0, len(category_sums))
    vertical_shifts = np.linspace(-0.5, 0.5, len(category_sums))

    for i, (wedge, category, value) in enumerate(zip(wedges, category_sums.index, category_sums.values)):
        ang = (wedge.theta2 - wedge.theta1) / 2. + wedge.theta1
        y = np.sin(np.deg2rad(ang))
        x = np.cos(np.deg2rad(ang))

        # Используем разные расстояния для каждой метки
        distance = distances[i]
        v_shift = vertical_shifts[i]

        label = f'{category}\n{value:,.0f}₽\n({value / category_sums.sum() * 100:.1f}%)'

        horizontalalignment = {-1: "right", 1: "left"}[int(np.sign(x))]
        connectionstyle = f"angle,angleA=0,angleB={ang}"

        ax.annotate(label,
                    xy=(x, y),
                    xytext=(distance * np.sign(x), y + v_shift),
                    horizontalalignment=horizontalalignment,
                    verticalalignment="center",
                    fontsize=9,  # Уменьшаем размер шрифта
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8),
                    arrowprops=dict(arrowstyle="-",
                                    connectionstyle=connectionstyle))

    plt.title('Структура расходов по категориям', pad=20, size=14)

    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=300)
    buf.seek(0)
    plt.close()
    return buf


def create_spending_line(user_id):
    plt.clf()
    plt.style.use('default')

    # Получаем данные
    df = get_user_transactions(user_id)
    daily_spending = df.groupby('date')['amount'].sum()

    # Создаем график
    fig, ax = plt.subplots(figsize=(12, 6))

    # Основная линия расходов
    ax.plot(daily_spending.index, daily_spending.values,
            marker='o', linewidth=2, markersize=6,
            color='#2ecc71', label='Ежедневные расходы')

    # Добавляем скользящее среднее
    ma7 = daily_spending.rolling(window=7).mean()
    ax.plot(ma7.index, ma7.values,
            color='#e74c3c', linestyle='--',
            linewidth=2, label='7-дневное среднее')

    # Оформление графика
    ax.fill_between(daily_spending.index, daily_spending.values,
                    alpha=0.3, color='#2ecc71')
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.set_title('Динамика расходов', pad=20, size=14)
    ax.set_xlabel('Дата')
    ax.set_ylabel('Сумма (₽)')
    ax.legend()

    # Поворот подписей дат
    plt.xticks(rotation=45)

    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=300)
    buf.seek(0)
    plt.close()
    return buf

def create_monthly_bar(user_id):
    plt.clf()
    df = get_user_transactions(user_id)

    # Группируем по месяцам
    monthly = df.groupby(df['date'].dt.strftime('%Y-%m'))['amount'].sum()

    plt.figure(figsize=(12, 6))
    monthly.plot(kind='bar')
    plt.title('Расходы по месяцам')
    plt.xticks(rotation=45)
    plt.grid(True)

    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close()
    return buf


def create_income_comparison(user_id):
    plt.clf()
    plt.style.use('default')

    df = get_user_transactions(user_id)
    df['date'] = pd.to_datetime(df['date'])

    # Разделяем исторические данные
    income = df[df['amount'] > 0].groupby('date')['amount'].sum()
    spending = df[df['amount'] < 0]['amount'].abs().groupby(df[df['amount'] < 0]['date']).sum()

    # Создаем прогноз на следующие 7 дней
    last_date = df['date'].max()
    forecast_dates = [last_date + pd.Timedelta(days=x) for x in range(1, 8)]

    # Простой прогноз на основе средних значений
    avg_income = income.mean()
    avg_spending = spending.mean()

    # Добавляем прогнозные значения
    for date in forecast_dates:
        income[date] = avg_income
        spending[date] = avg_spending

    # Создаем график
    fig, ax = plt.subplots(figsize=(15, 8))

    # Готовим данные для визуализации
    all_dates = sorted(list(set(income.index) | set(spending.index)))
    historical_dates = [d for d in all_dates if d <= last_date]
    future_dates = [d for d in all_dates if d > last_date]

    bar_width = 0.35
    x = np.arange(len(all_dates))

    # Рисуем исторические данные
    income_values = [income[d] if d in income.index else 0 for d in all_dates]
    spending_values = [spending[d] if d in spending.index else 0 for d in all_dates]

    # Исторические данные
    ax.bar(x[:len(historical_dates)], income_values[:len(historical_dates)],
           bar_width, label='Доходы', color='#2ecc71', alpha=0.7)
    ax.bar(x[:len(historical_dates)] + bar_width, spending_values[:len(historical_dates)],
           bar_width, label='Расходы', color='#e74c3c', alpha=0.7)

    # Прогнозные данные (более прозрачные)
    ax.bar(x[len(historical_dates):], income_values[len(historical_dates):],
           bar_width, label='Прогноз доходов', color='#2ecc71', alpha=0.3)
    ax.bar(x[len(historical_dates):] + bar_width, spending_values[len(historical_dates):],
           bar_width, label='Прогноз расходов', color='#e74c3c', alpha=0.3)

    # Добавляем вертикальную линию, разделяющую факт и прогноз
    plt.axvline(x=len(historical_dates) - 0.5, color='black', linestyle='--', alpha=0.5)
    plt.text(len(historical_dates) - 0.5, plt.ylim()[1], 'Прогноз →',
             rotation=90, va='top', ha='right')

    # Оформление
    plt.title('Сравнение доходов и расходов с прогнозом', size=16, pad=20)
    plt.xlabel('Дата', size=12)
    plt.ylabel('Сумма (₽)', size=12)

    # Настраиваем оси
    plt.xticks(x + bar_width / 2,
               [d.strftime('%d.%m') for d in all_dates],
               rotation=45)

    # Добавляем сетку
    plt.grid(True, axis='y', linestyle='--', alpha=0.7)

    # Статистика
    stats_text = (
        f'📈 Средний доход: {avg_income:,.0f}₽\n'
        f'📉 Средний расход: {avg_spending:,.0f}₽\n'
        f'🔮 Прогноз баланса через 7 дней: {(avg_income - avg_spending) * 7:,.0f}₽'
    )

    plt.text(0.02, 0.95, stats_text,
             transform=ax.transAxes,
             bbox=dict(facecolor='white',
                       edgecolor='gray',
                       alpha=0.8,
                       boxstyle='round,pad=0.5'),
             verticalalignment='top',
             fontsize=10)

    plt.legend(loc='upper right')

    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=300)
    buf.seek(0)
    plt.close()
    return buf


# Утро Уведомления:
def get_top_categories(user_id, days=30):
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute('''
        SELECT category, SUM(ABS(amount)) as total
        FROM transactions
        WHERE user_id = ? AND amount < 0
        AND date >= datetime('now', ?) 
        GROUP BY category
        ORDER BY total DESC
        LIMIT 3
    ''', (user_id, f'-{days} days'))
    top_categories = c.fetchall()
    conn.close()
    return top_categories


def generate_progress_bar(current, total, length=10):
    filled = int(length * current / total)
    return f"[{'█' * filled}{'░' * (length - filled)}]"


def predict_balance(total_balance, avg_daily_spending, days_until_salary):
    predicted = total_balance - (avg_daily_spending * days_until_salary)
    return predicted


def generate_daily_balance_forecast(total_balance, daily_budget, days_until_salary):
    forecast = []
    for day in range(days_until_salary):
        date = datetime.now() + timedelta(days=day)
        balance = total_balance - (daily_budget * day)
        forecast.append((date, balance))
    return forecast


def format_forecast_message(forecast, daily_budget):
    message = "\n📊 *Прогноз доступных средств:*\n"
    for date, balance in forecast:
        if balance > daily_budget * 3:
            emoji = "✅"
        elif balance > daily_budget:
            emoji = "💚"
        elif balance > 0:
            emoji = "⚠️"
        else:
            emoji = "🚫"
        message += f"• {date.strftime('%d.%m')}: {emoji} *{balance:.2f}* ₽\n"
    return message


def get_budget_status(daily_budget, avg_daily_spending):
    savings = daily_budget - avg_daily_spending

    if daily_budget <= 0:
        return "🚨 *Критическая ситуация!*\n_Срочно требуется пополнение баланса и временная остановка расходов_"

    if savings >= daily_budget * 0.5:
        return f"🌟 *Превосходно!* Вы экономите *{savings:.2f}* ₽ в день\n_Отличный результат, продолжайте в том же духе_"

    if savings >= daily_budget * 0.25:
        return f"✨ *Очень хорошо!* Экономия *{savings:.2f}* ₽ в день\n_Ваши финансовые привычки работают правильно_"

    if savings > 0:
        return f"👍 *Хорошо!* Экономия *{savings:.2f}* ₽ в день\n_Есть небольшой запас для непредвиденных расходов_"

    if savings > -daily_budget * 0.25:
        return f"⚠️ *Внимание!* Перерасход *{abs(savings):.2f}* ₽ в день\n_Рекомендуется пересмотреть необязательные траты_"

    if savings > -daily_budget * 0.5:
        return f"🔴 *Серьезный перерасход!* *{abs(savings):.2f}* ₽ в день\n_Необходимо сократить расходы или найти дополнительный доход_"

    return f"⛔️ *Критический перерасход!* *{abs(savings):.2f}* ₽ в день\n_Требуется срочный пересмотр финансовой стратегии_"


def calculate_daily_budget(user_id):
    total_balance = 0
    cards = get_cards(user_id)
    for _, balance in cards:
        total_balance += balance

    monthly_payments = 0
    salary_dates = get_salary_dates(user_id)

    if salary_dates:
        first_date, second_date = salary_dates
        next_first = get_next_salary_date(first_date)
        next_second = get_next_salary_date(second_date)
        next_salary = min(next_first, next_second)
        days_until_salary = (next_salary - datetime.now()).days + 1

        available_amount = total_balance - monthly_payments
        daily_budget = available_amount / days_until_salary if days_until_salary > 0 else 0

        _, avg_spending = get_stats_by_card(user_id, 30)
        avg_daily_spending = avg_spending / 30 if avg_spending else 0

        return {
            'daily_budget': daily_budget,
            'avg_daily_spending': avg_daily_spending,
            'days_until_salary': days_until_salary,
            'total_balance': total_balance,
            'available_amount': available_amount,
            'first_date': first_date,
            'second_date': second_date
        }
    return None


def export_to_excel(user_id):
    conn = sqlite3.connect('finance.db')

    # Получаем данные о транзакциях
    transactions_query = '''
        SELECT 
            datetime(t.date, '+5 hours') as date,
            c.card_name,
            t.category,
            t.amount
        FROM transactions t
        JOIN cards c ON t.card_id = c.id
        WHERE t.user_id = ?
        ORDER BY t.date DESC
    '''

    # Получаем данные о картах
    cards_query = '''
        SELECT card_name, balance
        FROM cards
        WHERE user_id = ?
    '''

    # Получаем данные о категориях
    categories_query = '''
        SELECT category_name
        FROM categories
        WHERE user_id = ?
    '''

    # Создаем DataFrame для каждого типа данных
    df_transactions = pd.read_sql_query(transactions_query, conn, params=(user_id,))
    df_cards = pd.read_sql_query(cards_query, conn, params=(user_id,))
    df_categories = pd.read_sql_query(categories_query, conn, params=(user_id,))

    # Форматируем данные
    df_transactions['date'] = pd.to_datetime(df_transactions['date'])
    df_transactions['type'] = df_transactions['amount'].apply(lambda x: 'Расход' if x < 0 else 'Пополнение')
    df_transactions['amount'] = df_transactions['amount'].abs()

    # Создаем Excel writer
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'finance_report_{timestamp}.xlsx'
    writer = pd.ExcelWriter(filename, engine='xlsxwriter')

    # Записываем данные на разные листы
    df_transactions.to_excel(writer, sheet_name='Транзакции', index=False)
    df_cards.to_excel(writer, sheet_name='Карты', index=False)
    df_categories.to_excel(writer, sheet_name='Категории', index=False)

    # Получаем объект workbook
    workbook = writer.book

    # Форматирование для листа транзакций
    worksheet_transactions = writer.sheets['Транзакции']
    money_format = workbook.add_format({'num_format': '# ##0.00 ₽'})
    date_format = workbook.add_format({'num_format': 'dd.mm.yyyy hh:mm'})

    worksheet_transactions.set_column('A:A', 18, date_format)  # Дата
    worksheet_transactions.set_column('B:B', 15)  # Карта
    worksheet_transactions.set_column('C:C', 15)  # Категория
    worksheet_transactions.set_column('D:D', 15, money_format)  # Сумма

    # Форматирование для листа карт
    worksheet_cards = writer.sheets['Карты']
    worksheet_cards.set_column('A:A', 15)  # Название карты
    worksheet_cards.set_column('B:B', 15, money_format)  # Баланс

    writer.close()

    return filename


@bot.message_handler(commands=['export'])
def handle_export(message):
    try:
        # Генерируем файл
        filename = export_to_excel(message.from_user.id)

        # Отправляем файл
        with open(filename, 'rb') as file:
            bot.send_document(
                message.chat.id,
                file,
                caption="📊 Ваш финансовый отчет"
            )

        # Удаляем временный файл
        os.remove(filename)

    except Exception as e:
        bot.reply_to(message, f"❌ Произошла ошибка при создании отчета: {str(e)}")

def send_morning_report():
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute('SELECT DISTINCT user_id FROM cards')
    users = c.fetchall()
    conn.close()

    weekdays = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']

    for user_id in users:
        user_id = user_id[0]
        budget_info = calculate_daily_budget(user_id)

        message = "🌅 *Доброе утро!*\n\n"

        cards = get_cards(user_id)
        message += "💳 *Текущие балансы:*\n"
        for card_name, balance in cards:
            message += f"{card_name}: *{balance:.2f}* ₽\n"

        if budget_info:
            if budget_info['total_balance'] < 0:
                message += "\n🚨 *Внимание! У вас отрицательный баланс!*\n"

            next_salary = min(get_next_salary_date(budget_info['first_date']),
                              get_next_salary_date(budget_info['second_date']))

            # Прогресс-бар до зарплаты
            days_passed = 30 - budget_info['days_until_salary']
            progress = days_passed / 30
            progress_bar = generate_progress_bar(days_passed, 30)

            message += f"\n📅 *Информация о зарплате:*\n"
            message += f"• Дней до зарплаты: *{budget_info['days_until_salary']}*\n"
            message += f"• Следующая зарплата: *{next_salary.strftime('%d.%m.%Y')}* ({weekdays[next_salary.weekday()]})\n"
            message += f"• Прогресс: {progress_bar} {int(progress * 100)}%\n"

            message += f"\n💰 Общий баланс: *{budget_info['total_balance']:.2f}* ₽"
            message += f"\n💵 Доступная сумма: *{budget_info['available_amount']:.2f}* ₽"

            # Прогноз баланса на дату ЗП
            predicted_balance = predict_balance(
                budget_info['total_balance'],
                budget_info['avg_daily_spending'],
                budget_info['days_until_salary']
            )
            message += f"\n\n🔮 *Прогноз баланса на дату ЗП:*\n"
            message += f"• При текущем темпе трат: *{predicted_balance:.2f}* ₽"
            if predicted_balance < 0:
                message += "\n_Рекомендуется пересмотреть расходы_"

            top_categories = get_top_categories(user_id)
            if top_categories:
                message += "\n\n📊 *Топ-3 категории расходов:*\n"
                for category, amount in top_categories:
                    message += f"• {category}: *{amount:.2f}* ₽\n"

            message += "\n📈 *Рекомендации по тратам:*\n"
            message += f"✅ Рекомендуемый дневной бюджет: *{budget_info['daily_budget']:.2f}* ₽\n"
            message += f"📈 Средний расход в день: *{budget_info['avg_daily_spending']:.2f}* ₽\n\n"
            message += get_budget_status(budget_info['daily_budget'], budget_info['avg_daily_spending'])

            # График доступности средств
            forecast = generate_daily_balance_forecast(
                budget_info['total_balance'],
                budget_info['daily_budget'],
                budget_info['days_until_salary']
            )
            message += format_forecast_message(forecast, budget_info['daily_budget'])



        else:
            message += "\n\n⚠️ Установите даты зарплаты для расчета бюджета (/salary)"

        try:
            bot.send_message(user_id, message, parse_mode='Markdown')
        except Exception as e:
            print(f"Error sending message to user {user_id}: {e}")
            continue


scheduler = BackgroundScheduler()
scheduler.add_job(
    send_morning_report,
    trigger=CronTrigger(hour=7, minute=0),
    id='morning_report',
    name='Send morning financial report',
    replace_existing=True
)
scheduler.start()


@bot.message_handler(commands=['testreport'])
def test_morning_report(message):
    send_morning_report()


# Запуск бота
bot.polling(none_stop=True)
