from src.main import app

if __name__ == '__main__':
    print('Starting dev server on http://0.0.0.0:5001')
    app.run(host='0.0.0.0', port=5001, debug=True)
