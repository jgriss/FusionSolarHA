This is an integration for Home Assistant that uses the following library :

https://pypi.org/project/fusion-solar-py/, which is used for reading data from the Huawei Fusion Solar cloud, with the common web login ( not API ).

This is especially useful if your PV system installer has not provided you with an API account.

To add this to your Home Assistant (HA) installation, one does the following:
 - on the HA machine go to the config folder (/config)
 - check the existence of the custom_components folder - create it if not existing and then copy the fusion_solar folder in there
 - go to the HA dashboard - Settings - Devices & Services
 - click on ADD INTEGRATION, search for FusionSolar and a login screen should appear
 - make sure the subdomain matches the one you see if you login on the fusion solar website - it will not work otherwise

 Once added, the sensors can be seen in the overview screen and used in further automation.
