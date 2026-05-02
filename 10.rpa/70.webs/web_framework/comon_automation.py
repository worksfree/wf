import pandas as pd
import time
import argparse
import os
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService

class WebAutomator:
    """
    Reads an Excel file with a sequence of actions and automates a web browser to execute them.
    """
    def __init__(self, actions_path: str):
        """
        Initializes the WebAutomator.

        Args:
            actions_path (str): The file path to the Excel file defining the automation steps.
        """
        print(f"Initializing WebAutomator with actions file: {actions_path}")
        self.actions_path = actions_path
        self.variables = {}
        self.driver = self._init_driver()
        self.df_actions = self._load_actions()

        self._action_dispatcher = {
            "navigate": self._do_navigate,
            "click": self._do_click,
            "input": self._do_input,
            "wait": self._do_wait,
            "uncheck": self._do_uncheck,
            "read_text": self._do_read_text,
            "read_attribute": self._do_read_attribute,
            "read_table": self._do_read_table,
            "accumulate": self._do_accumulate,
            "run_filter": self._do_run_filter,
            "save_csv": self._do_save_csv,
            # Loop actions are handled specially in the `run` method
        }

    def _init_driver(self) -> webdriver.Chrome:
        """Initializes the Selenium WebDriver."""
        print("Initializing Chrome WebDriver...")
        options = webdriver.ChromeOptions()
        # Add any desired options here
        # options.add_argument("--headless")
        service = ChromeService(executable_path=ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.implicitly_wait(5) # Default implicit wait
        return driver

    def _load_actions(self) -> pd.DataFrame:
        """Loads the actions from the specified Excel file."""
        print(f"Loading actions from {self.actions_path}...")
        df = pd.read_excel(self.actions_path).fillna('')
        df = df.sort_values(by="Step", ascending=True)
        print(f"Loaded {len(df)} steps.")
        return df

    def _get_element(self, xpath: str, wait_time: int = 10):
        """Finds and returns a web element using XPath with an explicit wait."""
        if not xpath:
            return None
        try:
            return WebDriverWait(self.driver, wait_time).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
        except TimeoutException:
            print(f"Error: Element not found after {wait_time} seconds for XPath: {xpath}")
            return None

    def run(self):
        """Executes the entire sequence of actions defined in the Excel file."""
        print("--- Starting automation sequence ---")
        try:
            step_index = 0
            while step_index < len(self.df_actions):
                row = self.df_actions.iloc[step_index]
                action_type = row["Action Type"]
                
                print(f"Step {row['Step']} ({action_type}): {row['UI Element Name']}")

                if action_type == "loop_start":
                    loop_start_index = step_index
                    step_index = self._handle_loop(loop_start_index)
                    continue

                if action_type in self._action_dispatcher:
                    self._action_dispatcher[action_type](row)
                elif action_type not in ["loop_end", "click_next"]: # These are handled in _handle_loop
                     print(f"Warning: Unknown Action Type '{action_type}' at Step {row['Step']}. Skipping.")

                step_index += 1

            print("--- Automation sequence finished ---")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        finally:
            print("Closing WebDriver.")
            self.driver.quit()

    def _handle_loop(self, loop_start_index: int) -> int:
        """
        Handles the logic for a loop block (from loop_start to loop_end).
        Returns the index of the step after the loop block.
        """
        loop_body_start_index = loop_start_index + 1
        
        try:
            loop_end_row = self.df_actions[self.df_actions['Action Type'] == 'loop_end'].iloc[0]
            loop_end_index = loop_end_row.name
        except IndexError:
            print("Error: 'loop_start' found but no corresponding 'loop_end'.")
            return len(self.df_actions) # Stop execution

        loop_body = self.df_actions.iloc[loop_body_start_index:loop_end_index]
        
        loop_start_row = self.df_actions.iloc[loop_start_index]
        max_pages_str = loop_start_row.get('Value', 'max_pages=99').split('=')[1]
        max_pages = int(max_pages_str)

        for i in range(max_pages):
            print(f"--- Loop Iteration {i+1}/{max_pages} ---")
            for _, row in loop_body.iterrows():
                action_type = row["Action Type"]
                print(f"  Step {row['Step']} ({action_type}): {row['UI Element Name']}")

                if action_type == "click_next":
                    element = self._get_element(row['Locator (XPath)'], wait_time=3)
                    if element and element.is_displayed() and element.is_enabled():
                        element.click()
                    else:
                        print("  'click_next' element not found or disabled. Ending loop.")
                        return loop_end_index + 1 # Exit loop
                elif action_type in self._action_dispatcher:
                    self._action_dispatcher[action_type](row)
                else:
                    print(f"  Warning: Unknown Action Type '{action_type}' in loop. Skipping.")
            
            # Small delay between pages to allow content to load
            time.sleep(1) 

        return loop_end_index + 1

    # --- Action Implementations ---

    def _do_navigate(self, row):
        self.driver.get(str(row['Value']))

    def _do_click(self, row):
        element = self._get_element(row['Locator (XPath)'])
        if element:
            element.click()

    def _do_input(self, row):
        element = self._get_element(row['Locator (XPath)'])
        if element:
            element.clear()
            element.send_keys(str(row['Value']))

    def _do_wait(self, row):
        wait_time = int(row.get('Value', 10))
        print(f"  Explicitly waiting for element up to {wait_time}s...")
        self._get_element(row['Locator (XPath)'], wait_time=wait_time)

    def _do_uncheck(self, row):
        element = self._get_element(row['Locator (XPath)'])
        if element and element.is_selected():
            element.click()

    def _do_read_text(self, row):
        element = self._get_element(row['Locator (XPath)'])
        if element:
            text = element.text
            self.variables[row['Output Variable']] = text
            print(f"  Stored '{text}' in variable '{row['Output Variable']}'")

    def _do_read_attribute(self, row):
        element = self._get_element(row['Locator (XPath)'])
        if element:
            attr_name = str(row['Value'])
            attr_value = element.get_attribute(attr_name)
            self.variables[row['Output Variable']] = attr_value
            print(f"  Stored attribute '{attr_name}={attr_value}' in variable '{row['Output Variable']}'")

    def _do_read_table(self, row):
        element = self._get_element(row['Locator (XPath)'])
        if element:
            # Use pandas to read the outer HTML of the table element
            html = element.get_attribute('outerHTML')
            try:
                dfs = pd.read_html(html)
                if dfs:
                    self.variables[row['Output Variable']] = dfs[0]
                    print(f"  Stored table with {len(dfs[0])} rows in variable '{row['Output Variable']}'")
            except Exception as e:
                print(f"  Error reading table: {e}")

    def _do_accumulate(self, row):
        source_var_name = str(row['Value'])
        target_var_name = str(row['Output Variable'])

        if source_var_name not in self.variables:
            print(f"  Warning: Source variable '{source_var_name}' for accumulate not found.")
            return

        source_data = self.variables[source_var_name]

        if target_var_name not in self.variables:
            self.variables[target_var_name] = source_data
            print(f"  Initialized and stored data in '{target_var_name}'")
        else:
            if isinstance(source_data, pd.DataFrame):
                self.variables[target_var_name] = pd.concat([self.variables[target_var_name], source_data], ignore_index=True)
            elif isinstance(source_data, list):
                self.variables[target_var_name].extend(source_data)
            print(f"  Accumulated data into variable '{target_var_name}'")

    def _do_run_filter(self, row):
        # This is a placeholder for more complex filtering logic.
        # For this example, it's a simple hardcoded filter.
        filter_name = str(row['Value'])
        source_var = str(row['Value']) # Assuming Value and Source are the same for simplicity
        target_var = str(row['Output Variable'])
        
        print(f"Running filter '{filter_name}'...")
        if source_var not in self.variables:
            print(f"  Warning: Variable '{source_var}' not found for filtering.")
            return
            
        data = self.variables[source_var]
        
        # Example filter logic
        if filter_name == "filter_ceo_age_and_cert" and isinstance(data, pd.DataFrame):
            # A dummy filter. In a real scenario, you'd have columns for this.
            # This just demonstrates the concept.
            print("  (Simulating filter) Dropping first row for demonstration.")
            self.variables[target_var] = data.drop(data.index[0]) if not data.empty else data
        else:
            print(f"  Filter '{filter_name}' not implemented. Copying data.")
            self.variables[target_var] = data

    def _do_save_csv(self, row):
        source_var = str(row['Output Variable'])
        file_path = str(row['Value'])

        if source_var not in self.variables:
            print(f"  Warning: Variable '{source_var}' not found for saving to CSV.")
            return

        data = self.variables[source_var]
        if isinstance(data, pd.DataFrame):
            data.to_csv(file_path, index=False, encoding='utf-8-sig')
            print(f"  Successfully saved data from '{source_var}' to '{file_path}'")
        else:
            print(f"  Warning: Data in '{source_var}' is not a table. Cannot save to CSV.")


def main():
    """
    Parses command-line arguments and runs the web automation.
    """
    parser = argparse.ArgumentParser(
        description="Runs a web automation task based on a specified Excel action file."
    )
    parser.add_argument(
        "--actions",
        required=True,
        help="Path to the Excel file containing the automation actions."
    )
    args = parser.parse_args()

    # Check if the actions file exists
    if not os.path.exists(args.actions):
        print(f"Error: The specified actions file does not exist: {args.actions}")
        sys.exit(1)

    # Initialize and run the automator
    try:
        automator = WebAutomator(actions_path=args.actions)
        automator.run()
    except Exception as e:
        print(f"A critical error occurred during automation: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
