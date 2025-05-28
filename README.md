This is to create an LLM/AI search.

I really need to work on the documentation.

## Usage

### Indexing
```shell
python index.py
```

### API
Within your `pipenv` environment, run:

```shell
uvicorn main:app --host 127.0.0.1 --port 8000
```

## Verification

Obviously, the above script needs to be available to where you're running it. It was run without a hostname, so the idea is that you would call it from `localhost` like so:

```shell
curl -X POST http://localhost:8000/ask \
-H "Content-Type: application/json" \
-d '{"query": "Tell me about Walt Whitman in Camden"}'
```

Then copy the `wp-ai-chat` folder and contents to your wordpress `/wp-content/plugins` directory.

For using within Wordpress, use a shortcode in any page or post:
```
[ai_chat]
```


## Notes
This is a work in progress. It should work, but might not. It's made for my own purposes, but hopefully it's useful to someone else. 