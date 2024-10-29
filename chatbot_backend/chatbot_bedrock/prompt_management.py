import boto3

client = boto3.client(
    service_name='bedrock-agent',
    region_name='us-west-2'
)


def get_prompt(prompt_id):
    response = client.get_prompt(
        promptIdentifier=prompt_id
    )
    prompt_text = response['variants'][0]['templateConfiguration']['text']['text']

    return prompt_text


def update_prompt(prompt_id, updated_prompt):
    response = client.update_prompt(
        promptIdentifier=prompt_id,
        name="DECIDE_ACTION",
        variants=[
            {
                'templateConfiguration': {
                    'text': {
                        'text': updated_prompt
                    }
                },
                'name': "DECIDE_ACTION",
                "templateType": "TEXT"
            }
        ]
    )

    return response['version']