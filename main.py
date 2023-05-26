import asyncio
import json
import asyncpg
import discord
from discord.ui.select import Select, Option

from discord.ext import commands

intents = discord.Intents.all()
intents.messages = True
intents.typing = False
intents.presences = False

bot = commands.Bot(command_prefix='!', intents=intents)


async def connect_to_db():
    bot.pg_con = await asyncpg.connect(user='postgres', password='21052105',
                                       database='saloon_db', host='localhost')


# Chargez le token depuis le fichier config.json
with open("config.json", "r") as f:
    config = json.load(f)


STOCK_CHANNEL_ID = 1103291698941014098
ACCOUNTING_CHANNEL_ID = 1103291840393908274
SALES_CHANNEL_ID = 1103291554220736552
SALARY_CHANNEL_ID = 1104529960984645642

stock_message_id = 1104858619922632744
accounting_message_id = 1104858622820892793
salary_message_id = 1104863489874464889


async def update_stock(category, item_name, sold_quantity):
    await bot.pg_con.execute(
        'UPDATE finished_products SET quantity = quantity - $1 WHERE category = $2 AND name = $3',
        sold_quantity, category, item_name)


async def update_accounting(employee_id, sold_price, item_name, quantity, category):
    # Récupérer le prix d'achat
    purchase_price = await bot.pg_con.fetchval(
        'SELECT buying_price FROM finished_products WHERE category = $1 AND name = $2',
        category, item_name)

    # Calculer le profit brut et la commission
    gross_profit = (sold_price - purchase_price) * quantity
    commission = gross_profit * 0.5  # 50% du profit brut va à la commission

    # Calculer le revenu après déduction de la commission
    net_revenue = gross_profit - commission

    # Récupérer l'argent total et le revenu existant
    total_money = await bot.pg_con.fetchval('SELECT total_money FROM accounting')
    existing_revenue = await bot.pg_con.fetchval('SELECT revenue FROM accounting')

    # Mettre à jour l'argent total et le revenu
    total_money += sold_price * quantity
    updated_revenue = existing_revenue + net_revenue

    # Mettre à jour la base de données
    await bot.pg_con.execute('UPDATE accounting SET total_money = $1, revenue = $2 WHERE id = 1',
                             total_money, updated_revenue)
    await bot.pg_con.execute('UPDATE salaries SET salary = salary + $1 WHERE employee_id = $2',
                             commission, str(employee_id))


async def update_stock_message():
    global stock_message_id

    stock_channel = bot.get_channel(STOCK_CHANNEL_ID)
    if not stock_message_id:
        stock_message = await stock_channel.send("Initialisation du message de stock...")
        stock_message_id = stock_message.id

    stock_message = await stock_channel.fetch_message(stock_message_id)

    # Fetch products from the database
    finished_products = await bot.pg_con.fetch(
        'SELECT name, quantity, selling_price, category FROM finished_products ORDER BY category, name')

    stock_text = "État du stockage :\n"
    current_category = None
    for product in finished_products:
        # Change the category when it's different
        if current_category != product['category']:
            current_category = product['category']
            stock_text += f"\n**{current_category.capitalize()}**\n"

        item_name = product["name"]
        item_quantity = product["quantity"]
        item_price = product["selling_price"]
        stock_text += f"{item_name}: {item_quantity} (Prix de vente: {item_price}€)\n"

    await stock_message.edit(content=stock_text)


async def update_accounting_message():
    global accounting_message_id

    accounting_channel = bot.get_channel(ACCOUNTING_CHANNEL_ID)
    if not accounting_message_id:
        accounting_message = await accounting_channel.send("Initialisation du message de comptabilité...")
        accounting_message_id = accounting_message.id

    accounting_message = await accounting_channel.fetch_message(accounting_message_id)

    # Récupérer les valeurs actuelles de la base de données
    total_money = await bot.pg_con.fetchval('SELECT total_money FROM accounting')
    revenue = await bot.pg_con.fetchval('SELECT revenue FROM accounting')
    tax_rate = await bot.pg_con.fetchval('SELECT tax_rate FROM accounting')

    # Calculer les taxes et le profit
    taxes = revenue * tax_rate
    profit = revenue - taxes

    # Préparer le texte à envoyer
    accounting_text = f"**Argent total :** {total_money}\n**Chiffre d'affaires :** {revenue}\n**Taxes ({tax_rate * 100}%) :** {taxes}\n**Bénéfice total :** {profit}"

    # Mettre à jour le message
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
        salary = await bot.pg_con.fetchval('SELECT salary FROM salaries WHERE employee_id = $1', int(user_id))
        salary_text += f"{member.name}: {salary}€\n"

    await salary_message.edit(content=salary_text)


async def send_sales_message():
    sales_channel = bot.get_channel(SALES_CHANNEL_ID)
    await sales_channel.send("Bienvenue sur le système de vente !", view=SalesView())

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

        # Fetch categories from the database
        categories = await bot.pg_con.fetch(
            'SELECT DISTINCT category FROM finished_products ORDER BY category')

        # Create options for each category
        options = [discord.SelectOption(label=category["category"], value=category["category"]) for category in categories]

        select_menu = CategorySelect(placeholder="Choisissez une catégorie", options=options)
        await interaction.followup.send("Veuillez choisir une catégorie :", view=select_menu, ephemeral=True)


from discord.ui import select

class CategorySelect(discord.ui.View):
    def __init__(self, placeholder, options):
        super().__init__()
        select_menu = discord.ui.Select(placeholder=placeholder, options=options)
        self.add_item(select_menu)

    @select.Option(label="Option 1", description="Description 1", value="1")
    async def callback(self, select, interaction):
        await interaction.response.send_message("Category selected!", ephemeral=True)
        await select.callback(interaction)

    async def on_timeout(self):
        await self.select_menu.send_message("Timeout reached.")






class ProductSelect(discord.ui.Select):
    def __init__(self, placeholder, options):
        super().__init__(placeholder=placeholder, options=options)

    async def callback(self, interaction: discord.Interaction):
        product = self.values[0]
        await interaction.response.send_message(f"Produit sélectionné : {product}", ephemeral=True)
        # Now you can proceed with the sales process


@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")
    await connect_to_db()  # Establish a connection to your database
    await update_stock_message()
    await update_accounting_message()
    await update_salary_message()
    await send_sales_message()


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


bot.run(config["token"])
