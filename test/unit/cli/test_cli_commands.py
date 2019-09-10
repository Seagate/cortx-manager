def test_alert_show(loop, imprt_redirection, server, csm_client):
    from csm.cli.command_factory import CommandFactory

    command = CommandFactory.get_command(['alerts', 'show'])
    response = loop.run_until_complete(csm_client.call(command))
    assert response.output()['response'] == command._action == 'show'


def test_alert_aknowledge(loop, imprt_redirection, server, csm_client):
    from csm.cli.command_factory import CommandFactory

    command = CommandFactory.get_command(
        ['alerts', 'acknowledge', '1', 'problem resolved'])
    response = loop.run_until_complete(csm_client.call(command))
    assert response.output()['response'] == command._action == 'acknowledge'
