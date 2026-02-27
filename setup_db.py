import asyncio
from backend.models.SQL import AuthorDB
from backend.models.data import Author
from backend.models.schema.enums import AuthorType
from backend.core.database.database_manager import DatabaseManager
from backend.models.SQL.base import BaseDB
    
async def create_key_authors():
    # Initialize database manager
    db = DatabaseManager()

    async with db.engine.begin() as conn:
        # Drop all existing tables
        await conn.run_sync(BaseDB.metadata.drop_all)
        
        # Create all tables with new schema
        await conn.run_sync(BaseDB.metadata.create_all)
    
    print("Database tables recreated successfully!")
    
    # Define key authors
    authors = [
        # Author(
        #     idname="elonmusk",
        #     aliases=["Kekius Maximus"],
        #     name="Elon Musk",
        #     type=AuthorType.TECH_LEADER,
        #     is_key_figure=True,
        #     affiliations=["Tesla", "SpaceX", "Starlink", "xAI", "Neuralink"],
        #     description="CEO of Tesla and SpaceX, founder of xAI. Known for his work in electric vehicles, space exploration, and artificial intelligence.",
        #     x_url="https://x.com/elonmusk",
        #     wikipedia_url="https://en.wikipedia.org/wiki/Elon_Musk"
        # ),

        Author(
            idname="karpathy",
            name="Andrej Karpathy",
            aliases=["badmephisto"],
            type=AuthorType.RESEARCHER,
            is_key_figure=True,
            description="Renowned computer scientist who co-founded OpenAI, served as Tesla's AI director, and founded Eureka Labs in 2024 to focus on AI education",
            website_url="https://karpathy.ai",
            x_url="https://x.com/karpathy",
            youtube_url="https://www.youtube.com/andrejkarpathy",
            wikipedia_url="https://en.wikipedia.org/wiki/Andrej_Karpathy",
            affiliations=["Tesla", "OpenAI", "Eureka Labs"]
        ),
        Author(
            idname="sama",
            name="Sam Altman",
            aliases=[],
            type=AuthorType.TECH_LEADER,
            is_key_figure=True,
            affiliations=["OpenAI", "Y Combinator"],
            description="CEO of OpenAI, ex-president of Y Combinator. Known for his work in artificial intelligence and entrepreneurship.",
            x_url="https://x.com/sama",
            wikipedia_url="https://en.wikipedia.org/wiki/Sam_Altman",
            linkedin_url="https://www.linkedin.com/in/sam-altman-4b290110/"
        ),
        
        # Author(
        #     idname="satyanadella",
        #     name="Satya Nadella",
        #     aliases=[],
        #     type=AuthorType.TECH_LEADER,
        #     is_key_figure=True,
        #     affiliations=["Microsoft", "Madrona Venture Group"],
        #     description="CEO and Chairman of Microsoft since 2014. Known for transforming Microsoft's culture and strategic direction, particularly in cloud computing and AI.",
        #     x_url="https://x.com/satyanadella",
        #     wikipedia_url="https://en.wikipedia.org/wiki/Satya_Nadella",
        #     linkedin_url="https://www.linkedin.com/in/satyanadella/"
        # ),
        # Author(
        #     idname="sundarpichai",
        #     name="Sundar Pichai",
        #     aliases=[],
        #     type=AuthorType.TECH_LEADER,
        #     is_key_figure=True,
        #     affiliations=["Google", "Alphabet"],
        #     description="CEO of Alphabet and Google since 2019. Led development of Chrome browser and Android OS before becoming CEO. Known for his leadership in AI, particularly with Google DeepMind and Gemini.",
        #     x_url="https://x.com/sundarpichai",
        #     wikipedia_url="https://en.wikipedia.org/wiki/Sundar_Pichai",
        #     linkedin_url="https://www.linkedin.com/in/sundarpichai",
        #     instagram_url="https://www.instagram.com/sundarpichai/"
        # )
        # Author(
        #     idname="PDChina",
        #     name="People's Daily",
        #     aliases=["人民日报"],
        #     type=AuthorType.MEDIA,
        #     is_key_figure=False,
        #     affiliations=["China"],
        #     description="The official newspaper of the People's Republic of China, published daily in Beijing.",
        #     website_url="https://en.people.cn",
        #     wikipedia_url="https://en.wikipedia.org/wiki/People%27s_Daily",
        #     weibo_url="https://weibo.com/u/2803301701"
        # ),        
    ]
    
    await db.create(AuthorDB, authors)
    print(f"{len(authors)} authors created successfully!")

if __name__ == "__main__":
    asyncio.run(create_key_authors())
