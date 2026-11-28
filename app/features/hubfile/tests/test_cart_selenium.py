from zipfile import ZipFile

import pytest
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from app.environment.host import get_host_for_selenium_testing
from app.selenium.common import close_driver, initialize_driver

pytestmark = pytest.mark.e2e


def test_download_models_from_dataset_and_explore(tmp_path):
    driver = initialize_driver(enable_downloads=True)
    try:
        host = get_host_for_selenium_testing()
        wait = WebDriverWait(driver, 20, ignored_exceptions=(StaleElementReferenceException,))
        dataset_button = (By.ID, "workbench-cart-button")
        count = (By.ID, "model-cart-count")
        driver.get(f"{host}/doi/10.1234/dataset3/files/file7.uvl")
        wait.until(EC.element_to_be_clickable(dataset_button)).click()
        wait.until(EC.text_to_be_present_in_element(count, "1"))
        wait.until(EC.element_to_be_clickable(dataset_button)).click()
        wait.until(EC.text_to_be_present_in_element(count, "0"))
        wait.until(EC.element_to_be_clickable(dataset_button)).click()
        wait.until(EC.text_to_be_present_in_element(count, "1"))

        driver.get(f"{host}/explore")
        driver.find_element(By.ID, "search-query").send_keys("file4.uvl")
        explore_button = (
            By.XPATH,
            "//div[@id='results-container']//div[contains(@class,'card-body')]"
            "[.//h2/a[normalize-space()='file4.uvl']]//button[@data-model-cart-id]",
        )

        def click_explore_model(browser):
            button = EC.element_to_be_clickable(explore_button)(browser)
            if not button:
                return False
            button.click()
            return True

        wait.until(click_explore_model)
        wait.until(EC.text_to_be_present_in_element(count, "2"))
        wait.until(click_explore_model)
        wait.until(EC.text_to_be_present_in_element(count, "1"))
        wait.until(click_explore_model)
        wait.until(EC.text_to_be_present_in_element(count, "2"))

        driver.find_element(By.ID, "model-cart-link").click()
        cart = (By.ID, "model-cart-files")
        wait.until(EC.text_to_be_present_in_element(cart, "file7.uvl"))
        wait.until(EC.text_to_be_present_in_element(cart, "file4.uvl"))
        assert driver.get_cookie("file_download_cookie") is None
        wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Download models"))).click()
        wait.until(lambda browser: browser.get_cookie("file_download_cookie"))
        if driver.capabilities.get("se:downloadsEnabled"):
            wait.until(lambda browser: "models.zip" in browser.get_downloadable_files())
            driver.download_file("models.zip", str(tmp_path))
            with ZipFile(tmp_path / "models.zip") as archive:
                paths = [name.split("/") for name in archive.namelist()]
                assert len(paths) == 2
                assert len({folder for folder, name in paths}) == 2
                assert {name for folder, name in paths} == {"file7.uvl", "file4.uvl"}
    finally:
        close_driver(driver)
