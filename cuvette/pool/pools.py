from motor import motor_asyncio

client = motor_asyncio.AsyncIOMotorClient()  # XXX

db = client['testdatabase']  # XXX

# Currently only one main pool for active machines
main_pool = db.machines
provision_pool = db.provisioning_machines
transform_pool = db.transforming_machines
reserved_pool = db.reserved_machines
failure_pool = db.failed_machines
