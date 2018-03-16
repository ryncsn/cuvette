from motor import motor_asyncio


# Currently we have one main pool for active machines
def get_machine_collection(db):
    return db.machines


def setup(settings):
    """
    Setup the database connection, and build pool indexes
    """
    if settings.DB_USER and settings.DB_PASSWORD:
        uri = "mongodb://%s:%s@%s/%s" % (settings.DB_USER, settings.DB_PASSWORD, settings.DB_HOST, settings.DB_NAME)
    else:
        uri = "mongodb://%s/%s" % (settings.DB_HOST, settings.DB_NAME)

    client = motor_asyncio.AsyncIOMotorClient(
        uri
    )

    db = client[settings.DB_NAME]

    # TODO get_machine_collection(db).create_index("hostname", unique=True) uniq or null
    get_machine_collection(db).create_index("magic", unique=True)

    return db
