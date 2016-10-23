import xbmc,xbmcaddon
import json

class SharedData:

	def __init__(self):
		self.folder = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile'));
		self.file_path = self.folder + "shared_data.json"

	def set(self, key, value):
		try:
			file = open(self.file_path)
			file_content = file.read()
			file.close()
		except:
			file_content = "{}"

		json_content = json.loads(file_content)
		json_content[key] = value
		file_content = json.dumps(json_content)

		file = open(self.file_path, "w")
		file.write(file_content)
		file.close()

	def get(self, key):
		try:
			file = open(self.file_path)
			file_content = file.read()
			file.close()
		except:
			file_content = "{}"

		json_content = json.loads(file_content)
		return json_content.get(key, "")