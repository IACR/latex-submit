from searchapp import config, create_app
conf = config.DebugConfig()
app = create_app(conf)
app.run(debug=True, host='0.0.0.0', port=5001)
