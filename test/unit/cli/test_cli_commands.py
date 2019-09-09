def test_get_request(loop, setup_redirection, server, csm_client, command):
    from csm.cli.command_factory import CommandFactory

    command = CommandFactory.get_command(['alerts', 'show'])
    response = loop.run_until_complete(csm_client.call(command))
    assert response.output()['response'] == command._action == 'show'
