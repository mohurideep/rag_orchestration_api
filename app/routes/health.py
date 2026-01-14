from flask_restx import Resource, Namespace

ns = Namespace("health", description="Health Check")

@ns.route("")
class Health(Resource):
    def get(self):
        """Health check endpoint"""
        return {"status": "ok"}