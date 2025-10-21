from data.db import declare_database, Base
import sqlalchemy as sa


class Test(Base):
    __tablename__ = 'test'
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String)


async def test():
    db = declare_database(url='sqlite+aiosqlite:///test.db')
    async with db() as session:
        await session.execute(sa.schema.CreateTable(Test.__table__))
        session.add(Test(name='test'))
        await session.commit()
        result_query = await session.execute(sa.select(Test))
        results = result_query.scalars().all()
        for result in results:
            print(result.as_dict())
        await session.close()


if __name__ == '__main__':
    import asyncio
    asyncio.run(test())
