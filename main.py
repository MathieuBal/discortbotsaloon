import discord
import asyncio
import os
import json
import sqlite3
from discord.ext import commands
from discord.ui import Button, View, Select

intents = discord.Intents.all()
intents.messages = True
intents.typing = False
intents.presences = False

bot = commands.Bot(command_prefix='!', intents=intents)

DB_NAME = "shop.db"
STOCK_CHANNEL_ID = 1103291698941014098
ACCOUNTING_CHANNEL_ID = 1103291840393908274
SALES_CHANNEL_ID = 1103291554220736552

stock_message_id = None
accounting_message_id = None

with open("config.json", "r") as f:
    config = json.load(f)

def create_db_connection():
    conn = sqlite3.connect(DB_NAME)
    return conn


def setup_database():
    conn = create_db_connection()
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS items
                     (category TEXT, nom TEXT, quantite INTEGER, prix_achat REAL, prix_vente REAL)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS accounting
                     (total_money REAL, revenue REAL, tax_rate REAL)''')

    conn.commit()
    conn.close()


def get_items():
    conn = create_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM items")
    items = cursor.fetchall()
    conn.close()

    item_stock = {}
    for item in items:
        category, nom, quantite, prix_achat, prix_vente = item
        if category not in item_stock:
            item_stock[category] = []
        item_stock[category].append({"nom": nom, "quantite": quantite, "prix_achat": prix_achat, "prix_vente": prix_vente})

    return item_stock


def get_accounting_data():
    conn = create_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM accounting")
    accounting_data = cursor.fetchone()

    if accounting_data:
        total_money, revenue, tax_rate = accounting_data
        return {"total_money": total_money, "revenue": revenue, "tax_rate": tax_rate}
    else:
        return {"total_money": 0, "revenue": 0, "tax_rate": 0.2}


def update_items(item_stock):
    conn = create_db_connection()
    cursor = conn.cursor()

    for category, items in item_stock.items():
        for item in items:
            cursor.execute("UPDATE items SET quantite=? WHERE category=? AND nom=?",
                           (item["quantite"], category, item["nom"]))

    conn.commit()
    conn.close()


def update_accounting_data(accounting_data):
    conn = create_db_connection()
    cursor = conn.cursor()

    cursor.execute("UPDATE accounting SET total_money=?, revenue=?, tax_rate=?",
                   (accounting_data["total_money"], accounting_data["revenue"], accounting_data["tax_rate"]))

    conn.commit()
    conn.close()


setup_database()
item_stock = get_items()
accounting_data = get_accounting_data()

total_money = accounting_data['total_money']
revenue = accounting_data['revenue']
tax_rate = accounting_data['tax_rate']

def update_database_files():
    update_items(item_stock)
    update_accounting_data(accounting_data)

async def update_stock_message():
    global stock_message_id

    stock_channel = bot.get_channel(STOCK_CHANNEL_ID)
    if not stock_message_id:
        stock_message = await stock_channel.send("Initialisation du message de stock...")
        stock_message_id = stock_message.id
    else:
        try:
            stock_message = await stock_channel.fetch_message(stock_message_id)
        except discord.NotFound:
            stock_message = await stock_channel.send("Le message de stock précédent est introuvable. "
                                                     "Initialisation d'un nouveau message de stock...")
            stock_message_id = stock_message.id

    stock_text = "État du stockage :\n"
    for category, items in item_stock.items():
        stock_text += f"\n**{category.capitalize()}**\n"
        for item_data in items:
            item_name = item_data["nom"]
            item_quantity = item_data["quantite"]
            stock_text += f"{item_name}: {item_quantity}\n"

    await stock_message.edit(content=stock_text)

async def update_accounting_message():
    global accounting_message_id

    accounting_channel = bot.get_channel(ACCOUNTING_CHANNEL_ID)
    if not accounting_message_id:
        accounting_message = await accounting_channel.send("Initialisation du message de comptabilité...")
        accounting_message_id = accounting_message.id

    accounting_message = await accounting_channel.fetch_message(accounting_message_id)

    taxes = revenue * tax_rate
    profit = revenue - taxes
    accounting_text = f"**Argent total :** {total_money}\n**Chiffre d'affaires :** {revenue}\n**Taxes (20%) :** {taxes}\n**Bénéfice total :** {profit}"

    await accounting_message.edit(content=accounting_text)

class SalesView(discord.ui.View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(style=discord.ButtonStyle.secondary, label="Vente", custom_id="sell_button")
    async def sell_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await interaction.followup.send("Veuillez choisir une catégorie :", view=CategoryView(),
                                        ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.secondary, label="Achat", custom_id="buy_button")
    async def buy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await interaction.followup.send("Fonction d'achat non encore implémentée.", ephemeral=True)



class CategoryView(discord.ui.View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(style=discord.ButtonStyle.secondary, label="Nourriture", custom_id="nourriture")
    async def nourriture_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_category(interaction, "nourriture")

    @discord.ui.button(style=discord.ButtonStyle.secondary, label="Boissons", custom_id="boissons")
    async def boissons_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_category(interaction, "boissons")

    @discord.ui.button(style=discord.ButtonStyle.secondary, label="Tabac", custom_id="tabac")
    async def tabac_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_category(interaction, "tabac")

    async def handle_category(self, interaction, category):
        items = item_stock[category]

        options = [discord.SelectOption(label=item['nom'], value=f"{category}:{item['nom']}") for item in items]

        select_menu = discord.ui.Select(placeholder=f"Choisissez un {category} à vendre", options=options)

        await interaction.response.send_message("Veuillez choisir un article à vendre :",
                                                view=ItemSelectView(select_menu, interaction.user), ephemeral=True)


class QuantityInputView(discord.ui.View):
    def __init__(self, user, item, item_price):
        super().__init__()
        self.user = user
        self.item = item
        self.item_price = item_price

    async def wait_for_quantity(self):
        print("enter in quantity mode..")
        def check(m):
            return m.author == self.user and m.content.isdigit()

        try:
            print("Waiting for quantity input...")
            quantity_response = await bot.wait_for('message', check=check, timeout=30)
            print(f"Quantity input received: {quantity_response.content}")
        except asyncio.TimeoutError:
            print("Quantity input timed out.")
            return None

        return int(quantity_response.content)

    async def on_timeout(self):
        pass


class ItemSelectView(discord.ui.View):
    def __init__(self, select_menu, user):
        super().__init__()
        self.user = user
        self.add_item(select_menu)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        print("Entered interaction_check method...")
        print(f"Interaction user: {interaction.user}, self.user: {self.user}")
        result = interaction.user == self.user
        print(f"Result: {result}")
        return result

    async def callback(self, interaction: discord.Interaction):
        print("Entered callback method...")
        category, item = self.values[0].split(':')
        item_data = None
        for i_data in item_stock[category]:
            if i_data["nom"] == item:
                item_data = i_data
                break

        print(f"Selected item: {item}")

        item_quantity = item_data["quantite"]
        item_price = item_data["prix_vente"]

        await interaction.response.send_message(f"Veuillez entrer la quantité de '{item}' à vendre :", ephemeral=True)
        print("Creating and waiting for quantity input view...")

        quantity_input_view = QuantityInputView(interaction.user, item, item_price)
        quantity = await quantity_input_view.wait_for_quantity()

        if quantity is None:
            await interaction.channel.send(content="Le temps imparti pour entrer la quantité est écoulé.",
                                           ephemeral=True)
            return

        price = item_price * quantity
        await interaction.channel.send(
            content=f"Ticket de caisse :\nArticle : {item}\nQuantité : {quantity}\nPrix total : {price}",
            ephemeral=True)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    await update_stock_message()

    sales_channel = bot.get_channel(SALES_CHANNEL_ID)
    await sales_channel.send(
        "Cliquez sur le bouton 'Vente' pour effectuer une vente ou sur 'Achat' pour effectuer un achat :",
        view=SalesView())

bot.run(config["token"])
