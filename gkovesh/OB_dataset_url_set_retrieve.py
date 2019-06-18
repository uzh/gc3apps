# coding: utf-8
import pybis
obs = pybis.Openbis("https://172.23.104.85")
obs.login(username="admin", password="changeit")
obs = pybis.Openbis("https://172.23.104.85", verify_certificates=False)
obs.login(username="admin", password="changeit")
obs.get_spaces()
obs.get_projects(space="BBLAB")
obs.get_experiment("20190108132301824-24")
obs.get_experiments()
obs.get_experiment("20190108133832745-25")
obs.get_collections()
obs.get_datasets()
obs.get_dataset("20190218144958335-31")
obs.get_dataset("20190218144958335-31")['tags']
res = obs.get_dataset("20190218144958335-31")
type(res)
res.tags
res = obs.get_dataset("20190218144958335-31")
res
res.file_list
res.props
res.get_files(start_folder='/var/tmp/openBIS/')
help(res.get_files)
res.get_files(start_folder='/')
res
res.props
res.props
res.props.URL = "/location"
res = obs.get_dataset("20190218144958335-31")
res.props
res.props.url = "/location"
res.save()
res.props.url = "http:///location"
res.save()
dir(res)
res = obs.get_dataset("20190218144958335-31")
res.props.url
get_ipython().run_line_magic('save', 'OB_dataset_url_set_retrieve ~0/')
