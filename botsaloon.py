import asyncio
import json
import os
import sys
import asyncpg
import discord
from discord.ext import commands

intents = discord.Intents.all()
intents.messages = True
intents.typing = False
intents.presences = False

bot = commands.Bot(command_prefix='!', intents=intents)


async def connect_to_db():
    bot.pg_con = await asyncpg.connect(user='postgres', password='21052105',
                                       database='saloon_db', host='localhost')

# Charger les stocks et la comptabilité depuis les fichiers JSON
with open("stocks.json", "r") as f:
    item_stock = json.load(f)

with open("accounting.json", "r") as f:
    accounting_data = json.load(f)

# Chargez le token depuis le fichier config.json
with open("config.json", "r") as f:
    config = json.load(f)

with open("salaries.json", "r") as f:
    salaries_data = json.load(f)


STOCK_CHANNEL_ID = 1103291698941014098
ACCOUNTING_CHANNEL_ID = 1103291840393908274
SALES_CHANNEL_ID = 1103291554220736552
SALARY_CHANNEL_ID = 1104529960984645642

stock_message_id = 1104858619922632744
accounting_message_id = 1104858622820892793
salary_message_id = 1104863489874464889


total_money = accounting_data['total_money']
revenue = accounting_data['revenue']
tax_rate = accounting_data['tax_rate']
commission_percentage = accounting_data['commission_percentage']



# Mettre à jour les stocks et la comptabilité dans les fichiers JSON
def update_json_files():
    with open("stocks.json", "w") as f:
        json.dump(item_stock, f)

    with open("accounting.json", "w") as f:
        json.dump(accounting_data, f)

    with open("salaries.json", "w") as f:
        json.dump(salaries_data, f)

def update_salaries_json():
    with open("salaries.json", "w") as f:
        json.dump(salaries_data, f)


def update_stock(category, item_name, sold_quantity):
    for item_data in item_stock[category]:
        if item_data["nom"] == item_name:
            item_data["quantite"] -= sold_quantity
            break


def update_accounting(seller_id, sold_price, item_name, quantity, category):
    global total_money, revenue

    # Récupérer le prix d'achat
    purchase_price = 0
    for item_data in item_stock[category]:
        if item_data["nom"] == item_name:
            purchase_price = item_data["prix_achat"]
            break

    # Calculer la commission
    profit = (sold_price - purchase_price) * quantity
    commission = profit * 0.25

    total_money += sold_price * quantity
    revenue += profit
    accounting_data['total_money'] = total_money
    accounting_data['revenue'] = revenue
    if str(seller_id) not in accounting_data:
        accounting_data[str(seller_id)] = 0
    accounting_data[str(seller_id)] += commission

    # Mettre à jour les données de salaire avec la commission calculée
    if str(seller_id) not in salaries_data:
        salaries_data[str(seller_id)] = 0
    salaries_data[str(seller_id)] += commission


async def update_stock_message():
    global stock_message_id

    stock_channel = bot.get_channel(STOCK_CHANNEL_ID)
    if not stock_message_id:
        stock_message = await stock_channel.send("Initialisation du message de stock...")
        stock_message_id = stock_message.id

    stock_message = await stock_channel.fetch_message(stock_message_id)

    stock_text = "État du stockage :\n"
    for category, items in item_stock.items():
        stock_text += f"\n**{category.capitalize()}**\n"
        for item_data in items:
            item_name = item_data["nom"]
            item_quantity = item_data["quantite"]
            item_price = item_data["prix_vente"]
            stock_text += f"{item_name}: {item_quantity} (Prix de vente: {item_price}€)\n"

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

async def update_salary_message():
    global salary_message_id

    salary_channel = bot.get_channel(SALARY_CHANNEL_ID)
    if not salary_message_id:
        salary_message = await salary_channel.send("Initialisation du message des salaires...")
        salary_message_id = salary_message.id

    salary_message = await salary_channel.fetch_message(salary_message_id)

    guild = bot.guilds[0]
    members = [member async for member in guild.fetch_members() if not member.bot]

    salary_text = "Salaires des employés :\n\n"
    for member in members:
        user_id = str(member.id)
        if user_id not in salaries_data:
            salaries_data[user_id] = 0
        salary_text += f"{member.name}: {salaries_data[user_id]}€\n"

    await salary_message.edit(content=salary_text)

async def send_sales_message():
    sales_channel = bot.get_channel(SALES_CHANNEL_ID)
    await sales_channel.send("Bienvenue sur le système de vente !", view=SalesView())


class SalesView(discord.ui.View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(style=discord.ButtonStyle.secondary, label="Vente", custom_id="sell_button")
    async def sell_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        # Créez un ticket et affichez-le
        ticket_view = TicketView(interaction.user)
        await interaction.followup.send("Ticket de caisse :\n(ajoutez des articles en choisissant une catégorie)",
                                        view=ticket_view, ephemeral=True)

        # Affichez les catégories pour que le vendeur puisse ajouter des articles
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

        select_menu = ItemSelect(placeholder=f"Choisissez un {category} à vendre", options=options,
                                 user=interaction.user)

        await interaction.response.send_message("Veuillez choisir un article à vendre :",
                                                view=ItemSelectView(select_menu), ephemeral=True)


class ItemSelectView(discord.ui.View):
    def __init__(self, select_menu):
        super().__init__()
        self.add_item(select_menu)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        print("Entered interaction_check method...")
        print(f"Interaction user: {interaction.user}, select_menu.user: {self.children[0].user}")
        result = interaction.user == self.children[0].user
        print(f"Result: {result}")
        return result

    async def on_timeout(self):
        pass


class QuantityInputView(discord.ui.View):
    def __init__(self, user, item, item_price):
        super().__init__(timeout=30)
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
        await self.message.edit(content="Le temps imparti pour entrer la quantité est écoulé.", view=None)


class ItemSelect(discord.ui.Select):
    def __init__(self, placeholder, options, user):
        super().__init__(placeholder=placeholder, options=options)
        self.user = user

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

        # Ajoutez l'article au ticket
        ticket_view = interaction.message.view
        await ticket_view.add_item(item, quantity)

        await interaction.response.send_message(
            content=f"Article ajouté au ticket : {item}\nQuantité : {quantity}", ephemeral=True)

        price = item_price * quantity
        await interaction.followup.send(
            content=f"Ticket de caisse :\nArticle : {item}\nQuantité : {quantity}\nPrix total : {price}",
            ephemeral=True)

        update_stock(category, item, quantity)
        update_accounting(interaction.user.id, item_price, item, quantity, category)
        update_salaries_json()

        await update_stock_message()
        await update_accounting_message()
        await update_salary_message()
        await send_sales_message()


        update_json_files()

async def add_item(self, item, quantity):
    self.items.append(item)
    self.quantities.append(quantity)


class TicketView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=None)
        self.user = user
        self.items = []
        self.quantities = []

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.user

    @discord.ui.button(style=discord.ButtonStyle.green, label="Valider", custom_id="validate_ticket")
    async def validate_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Construisez le résumé du ticket et envoyez-le
        ticket_details = "Ticket de caisse :\n"
        for i in range(len(self.items)):
            ticket_details += f"{self.items[i]}: {self.quantities[i]}\n"

        await interaction.response.send_message(ticket_details, ephemeral=True)
        self.stop()




@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")
    await update_stock_message()
    await update_accounting_message()
    await update_salary_message()
    await send_sales_message()


    sales_channel = bot.get_channel(SALES_CHANNEL_ID)
    await sales_channel.send("Bienvenue sur le système de vente !", view=SalesView())


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.startswith("!quit"):
        await bot.close()

    if message.content.startswith("!update"):
        await update_stock_message()
        await update_accounting_message()
        await update_salary_message()

    await bot.process_commands(message)


async def on_disconnect():
    print("Bot disconnected.")


bot.run(config["token"])
