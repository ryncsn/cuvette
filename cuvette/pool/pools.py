from motor import motor_asyncio


# Currently we have one main pool for active machines
def get_main_pool(db):
    return db.machines


# A failure pool to reserve failed machines
def get_failure_pool(db):
    return db.failed_machines


def setup(settings):
    """
    Setup the database connection, and build pool indexes
    """
    uri = "mongodb://%s" % settings.DB_HOST
    if settings.DB_USER and settings.DB_PASSWORD:
        uri = '%s:%s@' % (settings.DB_USER, settings.DB_PASSWORD) + uri

    client = motor_asyncio.AsyncIOMotorClient(
        uri
    )

    db = client[settings.DB_NAME]

    # TODO get_main_pool(db).create_index("hostname", unique=True) uniq or null

    return db
