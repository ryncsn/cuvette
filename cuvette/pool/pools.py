from motor import motor_asyncio

client = motor_asyncio.AsyncIOMotorClient()  # XXX

db = client['testdatabase']  # XXX

# Currently we have one main pool for active machines
main_pool = db.machines
# A failure pool to reserve failed machines
failure_pool = db.failed_machines
