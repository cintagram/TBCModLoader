from typing import Any, Optional

import bs4
import cloudscraper  # type: ignore
import requests

from tbcml import core


class Apk:
    def __init__(
        self,
        game_version: "core.GameVersion",
        country_code: "core.CountryCode",
        apk_folder: Optional["core.Path"] = None,
    ):
        self.game_version = game_version
        self.country_code = country_code
        self.package_name = self.get_package_name()

        if apk_folder is None:
            apk_folder = self.get_default_apk_folder()
        self.apk_folder = apk_folder
        self.locale_manager = core.LocalManager.from_config()

        self.smali_handler: Optional[core.SmaliHandler] = None

        self.init_paths()

        self.key = None
        self.iv = None

        self.libs: dict[str, core.Lib] = {}

    @staticmethod
    def from_format_string(
        format_string: str,
        apk_folder: Optional["core.Path"] = None,
    ) -> "Apk":
        cc, gv, _ = format_string.split(" ")
        gv = core.GameVersion.from_string(gv)
        cc = core.CountryCode.from_code(cc)
        return Apk(
            game_version=gv,
            country_code=cc,
            apk_folder=apk_folder,
        )

    def get_id(self) -> str:
        return f"{self.country_code.get_code()} {self.game_version.to_string()}"

    def init_paths(self):
        self.apk_folder.generate_dirs()
        self.server_path = self.apk_folder.add(
            f"{self.country_code.get_code()}_server_packs"
        )
        self.output_path = self.apk_folder.add(
            f"{self.game_version}{self.country_code.get_code()}"
        )

        self.final_apk_path = self.output_path.add(f"{self.package_name}-modded.apk")
        self.apk_path = self.output_path.add(f"{self.package_name}-original.apk")

        self.extracted_path = (
            self.output_path.add("extracted").remove_tree().generate_dirs()
        )
        self.decrypted_path = self.output_path.add("decrypted").generate_dirs()
        self.packs_path = self.output_path.add("packs").generate_dirs()
        self.modified_packs_path = (
            self.output_path.add("modified_packs").remove_tree().generate_dirs()
        )
        self.original_extracted_path = self.output_path.add(
            "original_extracted"
        ).generate_dirs()

        self.temp_path = self.output_path.add("temp").remove_tree().generate_dirs()

    def get_packs_lists(self) -> list[tuple["core.Path", "core.Path"]]:
        files: list[tuple[core.Path, core.Path]] = []
        for file in self.packs_path.get_files():
            if file.get_extension() != "pack":
                continue
            list_file = file.change_extension("list")
            if self.is_java() and "local" in file.basename().lower():
                list_file = list_file.change_name(
                    f"{file.get_file_name_without_extension()[:-1]}1.list"
                )
            if list_file.exists():
                files.append((file, list_file))
        return files

    def get_packs(self) -> list["core.Path"]:
        packs_list = self.get_packs_lists()
        return [pack[0] for pack in packs_list]

    def copy_packs(self):
        self.packs_path.remove_tree().generate_dirs()
        packs = self.get_pack_location().get_files()
        for pack in packs:
            if pack.get_extension() == "pack" or pack.get_extension() == "list":
                pack.copy(self.packs_path)

    def copy_extracted(self):
        self.extracted_path.remove_tree().generate_dirs()
        self.original_extracted_path.copy(self.extracted_path)

    @staticmethod
    def check_apktool_installed() -> bool:
        cmd = core.Command("apktool -version", False)
        res = cmd.run()
        return res.exit_code == 0

    @staticmethod
    def check_jarsigner_installed() -> bool:
        cmd = core.Command("jarsigner", False)
        res = cmd.run()
        return res.exit_code == 0

    @staticmethod
    def check_keytool_installed() -> bool:
        cmd = core.Command("keytool", False)
        res = cmd.run()
        return res.exit_code == 0

    def check_display_apktool_error(self) -> bool:
        if self.check_apktool_installed():
            return True
        message = "Apktool is not installed. Please install it and add it to your PATH. You can download it from https://ibotpeaches.github.io/Apktool/install/"
        print(message)
        return False

    def check_display_jarsigner_error(self) -> bool:
        if self.check_jarsigner_installed():
            return True
        message = (
            "Jarsigner is not installed. Please install it and add it to your PATH."
        )
        print(message)
        return False

    def check_display_keytool_error(self) -> bool:
        if self.check_keytool_installed():
            return True
        message = "Keytool is not installed. Please install it and add it to your PATH."
        print(message)
        return False

    def extract(self):
        if self.original_extracted_path.has_files():
            self.copy_extracted()
            self.copy_packs()
            self.libs = self.get_libs()
            return

        if not self.check_display_apktool_error():
            return

        cmd = core.Command(
            f"apktool d -f -s {self.apk_path} -o {self.original_extracted_path}", False
        )
        res = cmd.run()
        if res.exit_code != 0:
            print(f"Failed to extract APK: {res.result}")
            return
        self.copy_extracted()
        self.copy_packs()
        self.libs = self.get_libs()

    def extract_smali(self):
        if not self.check_display_apktool_error():
            return

        with core.TempFolder() as temp_folder:
            cmd = core.Command(f"apktool d -f {self.apk_path} -o {temp_folder}", False)
            res = cmd.run()
            if res.exit_code != 0:
                print(f"Failed to extract APK: {res.result}")
                return
            folders = temp_folder.glob("smali*")
            for folder in folders:
                new_folder = self.extracted_path.add(folder.basename())
                folder.copy(new_folder)

    def pack(self):
        if not self.check_display_apktool_error():
            return
        cmd = core.Command(
            f"apktool b {self.extracted_path} -o {self.final_apk_path}", False
        )
        res = cmd.run()
        if res.exit_code != 0:
            print(f"Failed to pack APK: {res.result}")
            return

    def sign(self):
        if not self.check_display_jarsigner_error():
            return
        if not self.check_display_keytool_error():
            return
        password = core.Config().get(core.ConfigKey.KEYSTORE_PASSWORD)
        key_store_name = "tbcml.keystore"
        key_store_path = core.Path.get_appdata_folder().add(key_store_name)
        if not key_store_path.exists():
            cmd = core.Command(
                f'keytool -genkey -v -keystore {key_store_path} -alias tbcml -keyalg RSA -keysize 2048 -validity 10000 -storepass {password} -keypass {password} -dname "CN=, OU=, O=, L=, S=, C="',
                False,
            )
            res = cmd.run()
            if res.exit_code != 0:
                print(f"Failed to generate keystore: {res.result}")
                return

        cmd = core.Command(
            f"jarsigner -verbose -sigalg SHA256withRSA -digestalg SHA-256 -keystore {key_store_path} {self.final_apk_path} tbcml",
            True,
        )
        res = cmd.run(password)
        if res.exit_code != 0:
            print(f"Failed to sign APK: {res.result}")
            return

    def set_key(self, key: str):
        self.key = key

    def set_iv(self, iv: str):
        self.iv = iv

    def add_packs_lists(
        self,
        packs: "core.GamePacks",
    ):
        files = packs.to_packs_lists(self.key, self.iv)
        for pack_name, pack_data, list_data in files:
            self.add_pack_list(pack_name, pack_data, list_data)

    def add_pack_list(
        self, pack_name: str, pack_data: "core.Data", list_data: "core.Data"
    ):
        pack_path = self.modified_packs_path.add(pack_name + ".pack")
        list_path = self.modified_packs_path.add(pack_name + ".list")
        pack_data.to_file(pack_path)
        list_data.to_file(list_path)

    def copy_modded_packs(self):
        for file in self.modified_packs_path.get_files():
            file.copy(self.get_pack_location().add(file.basename()))

    def load_packs_into_game(
        self,
        packs: "core.GamePacks",
    ):
        self.add_packs_lists(packs)
        core.LibFiles(self).patch()
        self.copy_modded_packs()
        self.pack()
        self.sign()
        self.copy_final_apk()

    def copy_final_apk(self):
        final_path = self.get_final_apk_path()
        if final_path == self.final_apk_path:
            return
        self.final_apk_path.copy(final_path)

    def get_final_apk_path(self) -> "core.Path":
        final_path = core.Config().get(core.ConfigKey.APK_COPY_PATH)
        if not final_path:
            return self.final_apk_path
        final_path = core.Path(final_path)
        if final_path.get_extension() == "apk":
            final_path.parent().generate_dirs()
        else:
            final_path.add(self.final_apk_path.basename())
        return final_path

    @staticmethod
    def get_default_apk_folder() -> "core.Path":
        folder = core.Path(core.Config().get(core.ConfigKey.APK_FOLDER)).generate_dirs()
        return folder

    def get_package_name(self) -> str:
        return f"jp.co.ponos.battlecats{self.country_code.get_patching_code()}"

    @staticmethod
    def get_all_downloaded() -> list["Apk"]:
        """
        Get all downloaded APKs

        Returns:
            list[APK]: List of APKs
        """
        all_apk_dir = core.Path(core.Config().get(core.ConfigKey.APK_FOLDER))
        apks: list[Apk] = []
        for apk_folder in all_apk_dir.get_dirs():
            name = apk_folder.get_file_name()
            country_code_str = name[-2:]
            if country_code_str not in core.CountryCode.get_all_str():
                continue
            cc = core.CountryCode.from_code(country_code_str)
            game_version_str = name[:-2]
            gv = core.GameVersion.from_string_latest(game_version_str, cc)
            apk = Apk(gv, cc)
            if apk.is_downloaded():
                apks.append(apk)

        apks.sort(key=lambda apk: apk.game_version.game_version, reverse=True)

        return apks

    @staticmethod
    def get_all_apks_cc(cc: "core.CountryCode") -> list["Apk"]:
        """
        Get all APKs for a country code

        Args:
            cc (country_code.CountryCode): Country code

        Returns:
            list[APK]: List of APKs
        """
        apks = Apk.get_all_downloaded()
        apks_cc: list[Apk] = []
        for apk in apks:
            if apk.country_code == cc:
                apks_cc.append(apk)
        return apks_cc

    @staticmethod
    def get_latest_downloaded_version_cc(
        cc: "core.CountryCode",
    ) -> "core.GameVersion":
        """
        Get latest downloaded APK version for a country code

        Args:
            cc (country_code.CountryCode): Country code

        Returns:
            game_version.GameVersion: Latest APK version
        """
        max_version = core.GameVersion(0)
        for apk in Apk.get_all_apks_cc(cc):
            if apk.game_version > max_version:
                max_version = apk.game_version
        return max_version

    @staticmethod
    def get_all_versions(
        cc: "core.CountryCode",
    ) -> list["core.GameVersion"]:
        """
        Get all APK versions

        Args:
            cc (country_code.CountryCode): Country code

        Returns:
            game_version.GameVersion: List of APK versions
        """
        if cc == core.CountryCode.EN or cc == core.CountryCode.JP:
            return Apk.get_all_versions_en(cc)
        url = Apk.get_apk_version_url(cc)
        scraper = cloudscraper.create_scraper()  # type: ignore
        resp = scraper.get(url)
        soup = bs4.BeautifulSoup(resp.text, "html.parser")
        versionwrapp = soup.find("ul", {"class": "ver-wrap"})
        if not isinstance(versionwrapp, bs4.element.Tag):
            return []
        versions: list[core.GameVersion] = []
        for version in versionwrapp.find_all("li"):
            if not isinstance(version, bs4.element.Tag):
                continue
            version_anchor = version.find("a")
            if not isinstance(version_anchor, bs4.element.Tag):
                continue
            version = version_anchor.get_attribute_list("data-dt-versioncode")[0]
            versions.append(core.GameVersion(int(version[:-1])))
        return versions

    @staticmethod
    def get_latest_version(cc: "core.CountryCode"):
        versions = Apk.get_all_versions(cc)
        if len(versions) == 0:
            return None
        return versions[0]

    def format(self):
        return f"{self.country_code.name} {self.game_version.format()} APK"

    @staticmethod
    def progress(
        progress: float,
        current: int,
        total: int,
        is_file_size: bool = False,
    ):
        total_bar_length = 70
        if is_file_size:
            current_str = core.FileSize(current).format()
            total_str = core.FileSize(total).format()
        else:
            current_str = str(current)
            total_str = str(total)
        bar_length = int(total_bar_length * progress)
        bar = "#" * bar_length + "-" * (total_bar_length - bar_length)
        print(
            f"\r[{bar}] {int(progress * 100)}% ({current_str}/{total_str})    ",
            end="",
        )

    def download_apk(self) -> bool:
        if self.apk_path.exists():
            return True
        if (
            self.country_code == core.CountryCode.EN
            or self.country_code == core.CountryCode.JP
        ):
            return self.download_apk_en(
                self.country_code == core.CountryCode.EN,
            )
        else:
            url = self.get_download_url()
            scraper = cloudscraper.create_scraper()  # type: ignore
            scraper.headers.update(
                {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36"
                }
            )
            stream = scraper.get(url, stream=True, timeout=10)
            total_length = int(stream.headers.get("content-length"))  # type: ignore
            dl = 0
            chunk_size = 1024
            buffer: list[bytes] = []
            for d in stream.iter_content(chunk_size=chunk_size):
                dl += len(d)
                buffer.append(d)

            apk = core.Data(b"".join(buffer))
            apk.to_file(self.apk_path)
            return True

    def download_apk_en(
        self,
        is_en: bool = True,
    ) -> bool:
        urls = Apk.get_en_apk_urls("the-battle-cats" if is_en else "the-battle-cats-jp")
        if not urls:
            print("Failed to get APK URLs")
            return False
        url = self.get_en_apk_url(urls[self.game_version.to_string()])
        if not url:
            print(f"Failed to get APK URL: {self.game_version.to_string()}")
            return False
        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-GB,en;q=0.9",
            "connection": "keep-alive",
            "sec-ch-ua": '"Google Chrome"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "Widnows",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36",
        }
        stream = core.RequestHandler(url, headers).get_stream()
        apk = core.Data(stream.content)
        apk.to_file(self.apk_path)
        return True

    def get_en_apk_url(self, apk_url: str):
        resp = core.RequestHandler(apk_url).get()
        soup = bs4.BeautifulSoup(resp.text, "html.parser")
        download_button = soup.find("button", {"class": "button download"})
        if not isinstance(download_button, bs4.element.Tag):
            return None
        return str(download_button.get_attribute_list("data-url")[0])

    @staticmethod
    def get_en_app_id(package_name: str) -> Optional[str]:
        url = f"https://{package_name}.en.uptodown.com/android/versions"
        try:
            resp = core.RequestHandler(url).get()
        except requests.RequestException:
            return None
        soup = bs4.BeautifulSoup(resp.text, "html.parser")
        app_details = soup.find("h1", {"id": "detail-app-name"})
        if not isinstance(app_details, bs4.element.Tag):
            return None
        app_id = app_details.get_attribute_list("code")[0]
        return app_id

    @staticmethod
    def get_en_apk_json(package_name: str) -> list[dict[str, Any]]:
        app_id = Apk.get_en_app_id(package_name)
        if app_id is None:
            return []
        url = f"https://{package_name}.en.uptodown.com/android/apps/{app_id}/versions?page[limit]=200&page[offset]=0"
        resp = core.RequestHandler(url).get()
        return resp.json()["data"]

    @staticmethod
    def get_en_apk_urls(package_name: str) -> Optional[dict[str, Any]]:
        json_data = Apk.get_en_apk_json(package_name)
        versions: list[str] = []
        urls: list[str] = []
        for data in json_data:
            versions.append(data["version"])
            urls.append(data["versionURL"])
        return dict(zip(versions, urls))

    def get_download_url(self) -> str:
        return f"https://d.apkpure.com/b/APK/jp.co.ponos.battlecats{self.country_code.get_patching_code()}?versionCode={self.game_version.game_version}0"

    @staticmethod
    def get_all_versions_en(
        cc: "core.CountryCode",
    ) -> list["core.GameVersion"]:
        apk_urls = Apk.get_en_apk_urls(
            "the-battle-cats-jp" if cc == core.CountryCode.JP else "the-battle-cats"
        )
        if apk_urls is None:
            return []
        versions: list[core.GameVersion] = []
        for version in apk_urls.keys():
            versions.append(core.GameVersion.from_string(version))
        return versions

    @staticmethod
    def get_apk_version_url(cc: "core.CountryCode") -> str:
        if cc == core.CountryCode.JP:
            url = "https://m.apkpure.com/%E3%81%AB%E3%82%83%E3%82%93%E3%81%93%E5%A4%A7%E6%88%A6%E4%BA%89/jp.co.ponos.battlecats/versions"
        elif cc == core.CountryCode.KR:
            url = "https://m.apkpure.com/%EB%83%A5%EC%BD%94-%EB%8C%80%EC%A0%84%EC%9F%81/jp.co.ponos.battlecatskr/versions"
        elif cc == core.CountryCode.TW:
            url = "https://m.apkpure.com/%E8%B2%93%E5%92%AA%E5%A4%A7%E6%88%B0%E7%88%AD/jp.co.ponos.battlecatstw/versions"
        else:
            raise ValueError(f"Country code {cc} not supported")
        return url

    def is_downloaded(self) -> bool:
        return self.apk_path.exists()

    def delete(self):
        self.output_path.remove_tree()

    @staticmethod
    def clean_up():
        for apk in Apk.get_all_downloaded():
            if apk.is_downloaded():
                continue
            apk.delete()

    def get_display_string(self) -> str:
        return f"{self.game_version.format()} <dark_green>({self.country_code})</>"

    def download_server_files(
        self,
        copy: bool = True,
    ):
        sfh = core.ServerFileHandler(self)
        sfh.extract_all()
        if copy:
            self.copy_server_files()

    def copy_server_files(self):
        server_path = self.get_server_path(self.country_code)
        if not server_path.exists():
            return
        for file in server_path.get_files():
            file.copy(self.packs_path.add(file.basename()))

    @staticmethod
    def get_server_path(cc: "core.CountryCode") -> "core.Path":
        apk_folder = Apk.get_default_apk_folder()
        return apk_folder.parent().add(f"{cc.get_code()}_server")

    @staticmethod
    def from_apk_path(apk_path: "core.Path") -> "Apk":
        cmd = f'aapt dump badging "{apk_path}"'
        result = core.Command(cmd).run()
        output = result.result
        version_name = ""
        package_name = ""
        for line in output.splitlines():
            if "versionName" in line:
                version_name = line.split("versionName='")[1].split("'")[0]
            if "package: name=" in line:
                package_name = line.split("name='")[1].split("'")[0]
        if version_name == "" or package_name == "":
            raise ValueError(
                f"Could not get version name or package name from {apk_path}"
            )

        cc_str = package_name.replace("jp.co.ponos.battlecats", "")
        cc = core.CountryCode.from_patching_code(cc_str)
        gv = core.GameVersion.from_string(version_name)
        apk = Apk(gv, cc)
        apk_path.copy(apk.apk_path)
        apk.original_extracted_path.remove_tree().generate_dirs()
        return apk

    def get_architectures(self):
        architectures: list[str] = []
        for folder in self.extracted_path.add("lib").get_dirs():
            architectures.append(folder.basename())
        return architectures

    def __str__(self):
        return self.get_display_string()

    def __repr__(self):
        return self.get_display_string()

    def get_libnative_path(self, architecture: str) -> "core.Path":
        if not self.is_java():
            return self.get_lib_path(architecture).add("libnative-lib.so")
        return self.get_lib_path(architecture).add("libbattlecats-jni.so")

    def is_java(self):
        return self.game_version < core.GameVersion.from_string("7.0.0")

    def parse_libnative(self, architecture: str) -> Optional["core.Lib"]:
        path = self.get_libnative_path(architecture)
        if not path.exists():
            return None
        return core.Lib(architecture, path)

    def get_smali_handler(self) -> "core.SmaliHandler":
        if self.smali_handler is None:
            self.smali_handler = core.SmaliHandler(self)
        return self.smali_handler

    def add_library(self, architecture: str, library_path: "core.Path"):
        libnative = self.libs.get(architecture)
        if libnative is None:
            print(f"Could not find libnative for {architecture}")
            return
        if not self.is_java():
            libnative.add_library(library_path)
            libnative.write()
        else:
            self.get_smali_handler().inject_load_library(library_path.basename())
        self.add_to_lib_folder(architecture, library_path)

    def get_lib_path(self, architecture: str) -> "core.Path":
        return self.extracted_path.add("lib").add(architecture)

    def import_libraries(self, lib_folder: "core.Path"):
        for architecture in self.get_architectures():
            libs_path = lib_folder.add(architecture)
            if not libs_path.exists():
                continue
            for lib in libs_path.get_files():
                self.add_library(architecture, lib)

    def add_to_lib_folder(self, architecture: str, library_path: "core.Path"):
        lib_folder_path = self.get_lib_path(architecture)
        library_path.copy(lib_folder_path)
        new_name = library_path.basename()
        if not library_path.basename().startswith("lib"):
            new_name = f"lib{library_path.basename()}"
        if library_path.get_extension() != "so":
            new_name = f"{new_name}.so"
        curr_path = lib_folder_path.add(library_path.basename())
        curr_path.rename(new_name, overwrite=True)

    def create_libgadget_config(self):
        json_data = {
            "interaction": {
                "type": "script",
                "path": f"/data/data/{self.package_name}/lib/libbc_script.js.so",
                "on_change": "reload",
            }
        }
        json = core.JsonFile.from_object(json_data)
        return json

    def add_libgadget_config(self, used_arcs: list[str]):
        config = self.create_libgadget_config()
        temp_file = self.temp_path.add("libfrida-gadget.config")
        config.to_data().to_file(temp_file)

        for architecture in used_arcs:
            self.add_to_lib_folder(architecture, temp_file)

        temp_file.remove()

    def add_libgadget_scripts(self, scripts: "core.FridaScripts"):
        for architecture in scripts.get_used_arcs():
            script_str = scripts.combine_scripts(architecture)
            script_path = self.temp_path.add("libbc_script.js.so")
            script_str.to_file(script_path)
            self.add_to_lib_folder(architecture, script_path)
            script_path.remove()

    def get_libgadgets(self) -> dict[str, "core.Path"]:
        folder = core.Config().get(core.ConfigKey.LIB_GADGETS_FOLDER)
        arcs = core.Path(folder).generate_dirs().get_dirs()
        libgadgets: dict[str, "core.Path"] = {}
        for arc in arcs:
            so_regex = ".*\\.so"
            files = arc.get_files(regex=so_regex)
            if len(files) == 0:
                continue
            libgadgets[arc.basename()] = files[0]
        return libgadgets

    def add_libgadget_sos(self, used_arcs: list[str]):
        for architecture, libgadget in self.get_libgadgets().items():
            if architecture not in used_arcs:
                continue
            self.add_library(architecture, libgadget)

    def add_frida_scripts(self, scripts: "core.FridaScripts"):
        used_arcs = scripts.get_used_arcs()
        self.add_libgadget_config(used_arcs)
        self.add_libgadget_scripts(scripts)
        self.add_libgadget_sos(used_arcs)

    def has_script_mods(self, bc_mods: list["core.Mod"]):
        if not bc_mods:
            return False
        scripts = core.FridaScripts([])
        for mod in bc_mods:
            scripts.add_scripts(mod.scripts)

        scripts.validate_scripts(self.country_code, self.game_version)
        return not scripts.is_empty()

    def add_script_mods(self, bc_mods: list["core.Mod"]):
        if not bc_mods:
            return
        scripts = core.FridaScripts([])
        for mod in bc_mods:
            scripts.add_scripts(mod.scripts)

        scripts.validate_scripts(self.country_code, self.game_version)
        if not scripts.is_empty():
            self.add_frida_scripts(scripts)

    def get_libs(self) -> dict[str, "core.Lib"]:
        libs: dict[str, "core.Lib"] = {}
        for architecture in self.get_architectures():
            libnative = self.parse_libnative(architecture)
            if libnative is None:
                continue
            libs[architecture] = libnative
        return libs

    @staticmethod
    def get_selected_apk() -> Optional["Apk"]:
        selected_apk = core.Config().get(core.ConfigKey.SELECTED_APK)
        if not selected_apk:
            return None
        return Apk.from_format_string(selected_apk)

    def get_manifest_path(self) -> "core.Path":
        return self.extracted_path.add("AndroidManifest.xml")

    def parse_manifest(self) -> "core.XML":
        return core.XML(self.get_manifest_path().read())

    def set_manifest(self, manifest: "core.XML"):
        manifest.to_file(self.get_manifest_path())

    def remove_arcs(self, arcs: list[str]):
        for arc in arcs:
            self.get_lib_path(arc).remove()

    def add_asset(self, asset_path: "core.Path"):
        asset_path.copy(self.extracted_path.add("assets").add(asset_path.basename()))

    def remove_asset(self, asset_path: "core.Path"):
        self.extracted_path.add("assets").add(asset_path.basename()).remove()

    def add_assets(self, asset_folder: "core.Path"):
        for asset in asset_folder.get_files():
            self.add_asset(asset)

    def add_assets_from_pack(self, pack: "core.PackFile"):
        if pack.is_server_pack(pack.pack_name):
            return
        temp_dir = self.temp_path.add("assets")
        pack.extract(temp_dir, encrypt=True)
        self.add_assets(temp_dir.add(pack.pack_name))
        temp_dir.remove()
        pack.clear_files()
        pack.add_file(
            core.GameFile(
                core.Data(pack.pack_name),
                f"empty_file_{pack.pack_name}",
                pack.pack_name,
                pack.country_code,
                pack.gv,
            )
        )
        pack.set_modified(True)

    def add_assets_from_game_packs(self, packs: "core.GamePacks"):
        for pack in packs.packs.values():
            self.add_assets_from_pack(pack)

    def add_file(self, file_path: "core.Path"):
        file_path.copy(self.extracted_path)

    def get_pack_location(self) -> "core.Path":
        if self.is_java():
            return self.extracted_path.add("res").add("raw")
        return self.extracted_path.add("assets")

    def add_audio(self, audio: "core.AudioFile"):
        audio.caf_to_little_endian().data.to_file(
            self.get_pack_location().add(audio.get_apk_name())
        )

    def add_audio_mods(self, bc_mods: list["core.Mod"]):
        for mod in bc_mods:
            for audio in mod.audio.audio_files.values():
                self.add_audio(audio)

    def get_all_audio(self) -> "core.Audio":
        audio_files: dict[str, "core.AudioFile"] = {}
        for file in self.get_pack_location().get_files():
            if not file.get_extension() == "caf" and not file.get_extension() == "ogg":
                continue
            audio_files[file.basename()] = core.AudioFile.from_file(file)
        for file in self.get_server_path(self.country_code).get_files():
            if not file.get_extension() == "caf" and not file.get_extension() == "ogg":
                continue
            audio_files[file.basename()] = core.AudioFile.from_file(file)

        return core.Audio(audio_files)

    def find_audio_path(self, audio: "core.AudioFile") -> Optional["core.Path"]:
        for file in self.get_pack_location().get_files():
            if not file.get_extension() == "caf" and not file.get_extension() == "ogg":
                continue
            if file.basename() == audio.get_apk_name():
                return file
        for file in self.get_server_path(self.country_code).get_files():
            if not file.get_extension() == "caf" and not file.get_extension() == "ogg":
                continue
            if file.basename() == audio.get_apk_name():
                return file
        return None

    def get_asset(self, asset_name: str) -> "core.Path":
        return self.extracted_path.add("assets").add(asset_name)

    def get_download_tsvs(self) -> list["core.Path"]:
        base_name = "download_%s.tsv"
        files: list["core.Path"] = []
        counter = 0
        while True:
            file = self.get_asset(base_name % counter)
            if not file.exists():
                break
            files.append(file)
            counter += 1
        return files

    def apply_mod_smali(self, mod: "core.Mod"):
        if mod.smali.is_empty():
            return
        self.get_smali_handler().inject_into_on_create(mod.smali.get_list())

    def set_allow_backup(self, allow_backup: bool):
        manifest = self.parse_manifest()
        path = "application"
        if allow_backup:
            manifest.set_attribute(path, "android:allowBackup", "true")
        else:
            manifest.set_attribute(path, "android:allowBackup", "false")
        self.set_manifest(manifest)

    def set_debuggable(self, debuggable: bool):
        manifest = self.parse_manifest()
        path = "application"
        if debuggable:
            manifest.set_attribute(path, "android:debuggable", "true")
        else:
            manifest.set_attribute(path, "android:debuggable", "false")
        self.set_manifest(manifest)

    def set_package_name(self, package_name: str):
        self.package_name = package_name
        manifest = self.parse_manifest()
        manifest.set_attribute("manifest", "package", package_name)

        strings_xml = self.extracted_path.add("res").add("values").add("strings.xml")
        strings_o = core.XML(strings_xml.read())
        strings = strings_o.get_elements("string")
        for string in strings:
            if string.get("name") == "package_name":
                string.text = package_name
                break
        strings_o.to_file(strings_xml)

        path = "application/provider"
        for provider in manifest.get_elements(path):
            attribute = manifest.get_attribute_name("android:authorities")
            name = provider.get(attribute)
            if name is None:
                continue

            parts = name.split(".")
            if len(parts) < 2:
                continue
            end = parts[-1]

            provider.set(attribute, package_name + "." + end)

        self.set_manifest(manifest)

    def set_modded_html(self, mods: list["core.Mod"]):
        template_file_name = "kisyuhen_01_top_en.html"
        template_file = (
            core.Path.get_files_folder()
            .add("assets", template_file_name)
            .read()
            .to_str()
        )
        mod_html = ""
        for mod in mods:
            mod_url = f"https://tbcml.net/mod/{mod.name}"
            mod_html += f'<a class="Buttonbig" href="{mod_url}">{mod.name}</a><br><br>'
        template_file = template_file.replace("{{modlist}}", mod_html)
        self.extracted_path.add("assets", template_file_name).write(
            core.Data(template_file)
        )

    def add_mod_files(self, mod: "core.Mod"):
        for file_name, data in mod.apk_files.items():
            self.extracted_path.add(file_name).write(data)

    def add_mods_files(self, mods: list["core.Mod"]):
        for mod in mods:
            self.add_mod_files(mod)

    def add_smali_mods(self, mods: list["core.Mod"]):
        for mod in mods:
            self.apply_mod_smali(mod)

    def load_mods(
        self,
        mods: list["core.Mod"],
        game_packs: Optional["core.GamePacks"] = None,
    ):
        if game_packs is None:
            game_packs = core.GamePacks.from_apk(self)
        game_packs.apply_mods(mods)
        self.add_mods_files(mods)
        self.set_allow_backup(True)
        self.set_debuggable(True)
        self.set_modded_html(mods)
        self.add_audio_mods(mods)
        self.add_script_mods(mods)
        self.add_smali_mods(mods)
        self.load_packs_into_game(game_packs)
