from standardweb.lib import cache
from standardweb.models import *

from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func


def extract_face(image, size):
    try:
        pix = image.load()
        for x in xrange(8, 16):
            for y in xrange(8, 16):
                # apply head accessory for non-transparent pixels
                if pix[x + 32, y][3] > 0:
                    pix[x, y] = pix[x + 32, y]
    except:
        pass

    return image.crop((8, 8, 16, 16)).resize((size, size))


def get_combat_data(player, server):
    pvp_kills = []
    pvp_deaths = []
    other_kills = []
    other_deaths = []

    pvp_kill_count = 0
    pvp_death_count = 0
    other_kill_count = 0
    other_death_count = 0

    deaths = DeathCount.query.filter_by(server=server, victim_id=player.id) \
        .options(joinedload('killer')).options(joinedload('death_type'))

    for death in deaths:
        if death.killer:
            pvp_deaths.append({
                'player': death.killer,
                'count': death.count
            })
            pvp_death_count += death.count
        else:
            other_deaths.append({
                'type': death.death_type.displayname,
                'count': death.count
            })
            other_death_count += death.count

    kills = KillCount.query.filter_by(server=server, killer_id=player.id) \
        .options(joinedload('kill_type'))

    for kill in kills:
        other_kills.append({
            'type': kill.kill_type.displayname,
            'count': kill.count
        })
        other_kill_count += kill.count

    kills = DeathCount.query.filter_by(server=server, killer_id=player.id) \
        .options(joinedload('victim')).options(joinedload('death_type'))

    for kill in kills:
        pvp_kills.append({
            'player': kill.victim,
            'count': kill.count
        })
        pvp_kill_count += kill.count

    pvp_kills = sorted(pvp_kills, key=lambda k: (-k['count'], k['player'].displayname.lower()))
    pvp_deaths = sorted(pvp_deaths, key=lambda k: (-k['count'], k['player'].displayname.lower()))
    other_deaths = sorted(other_deaths, key=lambda k: (-k['count'], k['type']))
    other_kills = sorted(other_kills, key=lambda k: (-k['count'], k['type']))

    return {
        'pvp_kill_count': pvp_kill_count,
        'pvp_death_count': pvp_death_count,
        'pvp_kills': pvp_kills,
        'pvp_deaths': pvp_deaths,
        'other_kill_count': other_kill_count,
        'other_death_count': other_death_count,
        'other_deaths': other_deaths,
        'other_kills': other_kills
    }


@cache.CachedResult('player', time=30)
def get_data_on_server(player, server):
    """
    Returns a dict of all the data for a particular player which
    consists of their global gameplay stats and the stats for the
    given server.
    """
    first_ever_seen = db.session.query(
        func.min(PlayerStats.first_seen)
    ).join(Server).filter(
        PlayerStats.player_id == player.id,
        Server.type == 'survival'
    ).scalar()

    if not first_ever_seen:
        return None

    last_seen = db.session.query(
        func.max(PlayerStats.last_seen)
    ).join(Server).filter(
        PlayerStats.player_id == player.id,
        Server.type == 'survival'
    ).scalar()

    total_time = db.session.query(
        func.sum(PlayerStats.time_spent)
    ).join(Server).filter(
        PlayerStats.player_id == player.id,
        Server.type == 'survival'
    ).scalar()

    ore_discoveries = OreDiscoveryCount.query.options(
        joinedload(OreDiscoveryCount.material_type)
    ).filter_by(
        player=player,
        server=server
    )

    ore_counts = {type: 0 for type in MaterialType.ORES}

    for ore in ore_discoveries:
        ore_counts[ore.material_type.type] += ore.count

    ore_counts = [(ore.displayname, ore_counts[ore.type]) for ore in MaterialType.get_ores()]

    stats = PlayerStats.query.filter_by(
        server=server,
        player=player
    ).first()

    server_stats = None
    if stats:
        server_stats = {
            'rank': stats.rank,
            'time_spent': h.elapsed_time_string(stats.time_spent),
            'pvp_logs': stats.pvp_logs,
            'group': stats.group,
            'is_leader': stats.is_leader,
            'is_moderator': stats.is_moderator,
            'ore_counts': ore_counts
        }

    online_now = datetime.utcnow() - last_seen < timedelta(minutes=1)

    return {
        'first_ever_seen': first_ever_seen,
        'last_seen': last_seen,
        'online_now': online_now,
        'total_time': h.elapsed_time_string(total_time),
        'combat_stats': get_combat_data(player, server),
        'server_stats': server_stats
    }
