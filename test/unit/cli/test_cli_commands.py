

def test_cli(loop, setup_redirection, server, scm_client, command):
    response = loop.run_until_complete(scm_client.call(command))
    a = 10
