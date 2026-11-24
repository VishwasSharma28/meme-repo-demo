def lambda_handler(event, context):
    name = event.get("name", "Tech Tuesday")

    print(f"Hello, {name}!")

    return {
        "statusCode": 200,
        "message": f"Lambda is working! Hello, {name}!"
    }