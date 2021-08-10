from datetime import date
from helpers import programmes_helper
from services.errors.entry_already_exists_error import EntryAlreadyExistsError
from services.errors.date_incorrect_error import DateIncorrectError
from services.errors.entry_not_found_error import EntryNotFoundError
import constants


class RanksService:
    def __init__(self, db_conn):
        self.db_conn = db_conn

    async def get_rank_details_for_programme_and_user(self, programme: str, year: int, user_id: str):
        if user_id is None:
            raise ValueError

        curr_rank = await self.db_conn.fetchrow('SELECT rank, is_private FROM ranks '
                                                'WHERE user_id = $1 AND programme = $2 AND year = $3',
                                                user_id, programme, year)

        return curr_rank

    async def add_rank(self, rank: int, programme: str, year: int, user_id: str = None, offer_date: date = None,
                       source: str = None, is_private: bool = False):
        if rank <= 0 or rank >= 10000 or programme not in programmes_helper.programmes \
                or year not in programmes_helper.programmes[programme].places:
            raise ValueError

        if user_id is not None:
            curr_rank = await self.db_conn.fetchrow('SELECT rank FROM ranks '
                                                    'WHERE user_id = $1 AND programme = $2 AND year = $3',
                                                    user_id, programme, year)
            if curr_rank is not None:
                raise EntryAlreadyExistsError

        if rank <= programmes_helper.programmes[programme].places[year]:
            if offer_date is None:
                offer_date = date(constants.current_year, 4, 15)
            else:
                raise DateIncorrectError

        await self.db_conn.execute(
            'INSERT INTO ranks (user_id, rank, programme, offer_date, is_private, source, year) '
            'VALUES ($1, $2, $3, $4, $5, $6, $7)',
            user_id, rank, programme, offer_date, is_private, source, year)

    async def delete_rank(self, user_id: str, programme: str, year: int):
        if programme is None:
            await self.db_conn.execute('DELETE FROM ranks WHERE user_id = $1 AND year = $2', user_id, year)
        else:
            if programme not in programmes_helper.programmes:
                raise ValueError
            await self.db_conn.execute('DELETE FROM ranks WHERE user_id = $1 AND programme = $2 AND year = $3',
                                       user_id, programme, year)

    async def set_offer_date(self, user_id: str, programme: str, offer_date: date, year: int):
        if programme not in programmes_helper.programmes or year not in programmes_helper.programmes[programme].places:
            raise ValueError

        rank = await self.db_conn.fetchval('SELECT rank FROM ranks WHERE user_id = $1 AND programme = $2 AND year = $3',
                                           user_id, programme, year)

        if not rank:
            raise EntryNotFoundError

        if rank <= programmes_helper.programmes[programme].places[year]:
            raise DateIncorrectError

        await self.db_conn.execute('UPDATE ranks SET offer_date = $1 '
                                   'WHERE user_id = $2 AND programme = $3 AND year = $4',
                                   offer_date, user_id, programme, year)

    async def get_top_ranks(self, year: int):
        rows = await self.db_conn.fetch('SELECT username, rank, programme FROM ranks '
                                        'JOIN user_data ON ranks.user_id = user_data.user_id '
                                        'WHERE (is_private IS NULL OR is_private = FALSE)'
                                        ' AND username IS NOT NULL AND year = $1 '
                                        'ORDER BY rank ASC',
                                        year)

        curr_programmes = set(map(lambda x: x[2], rows))
        grouped_ranks = [(p, [row for row in rows if row[2] == p]) for p in curr_programmes]

        grouped_ranks.sort(key=lambda g: len(g[1]), reverse=True)

        return grouped_ranks

    async def get_is_private(self, user_id: str, year: int) -> bool:
        is_private = await self.db_conn.fetchval('SELECT is_private FROM ranks '
                                                 'WHERE user_id = $1 AND year = $2',
                                                 user_id, year)
        return is_private

    async def get_has_only_one_rank(self, user_id: str, year: int) -> bool:
        is_private = await self.db_conn.fetchval('SELECT COUNT(is_private) FROM ranks '
                                                 'WHERE user_id = $1 AND year = $2',
                                                 user_id, year)
        return is_private == 1

    async def get_is_private_programme(self, user_id: str, programme: str, year: int) -> bool:
        if programme not in programmes_helper.programmes:
            raise ValueError

        is_private = await self.db_conn.fetchval('SELECT is_private FROM ranks '
                                                 'WHERE user_id = $1 AND programme = $2 AND year = $3',
                                                 user_id, programme, year)
        return is_private

    async def set_is_private(self, user_id: str, is_private: bool, year: int):
        await self.db_conn.execute('UPDATE ranks SET is_private = $1 '
                                   'WHERE user_id = $2 AND year = $3',
                                   is_private, user_id, year)

    async def set_is_private_programme(self, user_id: str, is_private: bool, programme: str, year: int):
        await self.db_conn.execute('UPDATE ranks SET is_private = $1 '
                                   'WHERE user_id = $2 AND programme = $3 AND year = $4',
                                   is_private, user_id, programme, year)
