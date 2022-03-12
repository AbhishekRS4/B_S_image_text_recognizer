import json
import requests
import streamlit as st
import http.client, urllib.request, urllib.parse, urllib.error, base64

def write_json_file(json_file_name, data_dict):
    fp = open(json_file_name, 'w')
    json.dump(data_dict, fp, sort_keys=True,
              indent=4, default=lambda o: o.__dict__)
    fp.close()
    return

def read_json_file(json_file_name):
    data_dict = json.load(open(json_file_name))
    return data_dict

def search_text_single_image():
    st.title("Text finder in images")
    image_urls_text_file = "https://stbbdimages.blob.core.windows.net/images/image_urls.txt"
    list_image_urls = get_images_list(image_urls_text_file)
    list_image_urls = list_image_urls.split("\n")

    min_value = 1
    num_images = len(list_image_urls)
    end_point = st.sidebar.text_input("Enter the Azure service end point", "cog-bbd.cognitiveservices.azure.com")
    api_key = st.sidebar.text_input("Enter the Azure service API key")
    image_index = st.sidebar.slider(f"Select image index ({min_value} - {num_images})", value=min_value, min_value=min_value, max_value=num_images)
    show_image = st.sidebar.checkbox("Display image", True)
    show_words = st.sidebar.checkbox("Display detected words", False)
    search_key_word = st.sidebar.text_input("Enter a key word to search", "example")

    st.write(f"Selected image index : {image_index}")

    st.header("Image URL")
    url_image = list_image_urls[image_index-1]
    st.write(url_image)

    if show_image:
        st.header("Image")
        st.image(url_image)

    if len(api_key) == 0:
        st.warning("API key is empty")
        return

    st.header("Words in the image")
    all_words, all_bounding_boxes = get_words_from_vision_api(url_image, end_point, api_key)

    if len(all_words) > 0:
        if show_words:
            for word in all_words:
                st.write(word)

        st.header("Keyword search result")
        if search_key_word in all_words:
            st.write(f"Word : {search_key_word}, is found in the image")
        else:
            st.write(f"Word : {search_key_word}, not found in the image")
    else:
        st.write("No words found")
    return

def search_text_multi_images():
    image_urls_text_file = "https://stbbdimages.blob.core.windows.net/images/image_urls.txt"
    list_image_urls = get_images_list(image_urls_text_file)
    list_image_urls = list_image_urls.split("\n")
    num_images = len(list_image_urls)

    search_key_word = st.sidebar.text_input("Enter a key word to search", "example")
    show_images = st.sidebar.checkbox("Display images", False)
    file_json = "data_images.json"
    try:
        data_dict_json = read_json_file(file_json)
    except:
        st.warning(f"File {file_json} does not exist")
        return

    all_images_key_found = []
    for key in data_dict_json.keys():
        words = data_dict_json[key]["word"]
        if search_key_word in words:
            all_images_key_found.append(key)

    num_images_key_found = len(all_images_key_found)
    st.header(f"Number of images with the key word : {search_key_word} is {num_images_key_found}")
    if show_images:
        if num_images_key_found > 0:
            for url_image in all_images_key_found:
                st.header(url_image)
                st.image(url_image)
    return

def save_detected_words():
    end_point = st.sidebar.text_input("Enter the Azure service end point", "cog-bbd.cognitiveservices.azure.com")
    api_key = st.sidebar.text_input("Enter the Azure service API key")
    start_button = st.sidebar.button("Start saving word detections")
    image_urls_text_file = "https://stbbdimages.blob.core.windows.net/images/image_urls.txt"
    list_image_urls = get_images_list(image_urls_text_file)
    list_image_urls = list_image_urls.split("\n")
    num_images = len(list_image_urls)

    data_dict_json = {}
    st.write("Starting to save the detected words")

    if len(api_key) == 0:
        st.warning("API key is empty")
        return

    if start_button:
        progress_bar = st.progress(0.0)

        for url_index in range(num_images):
            inner_data_dict = {}
            url_image = list_image_urls[url_index]
            all_words, all_bounding_boxes = get_words_from_vision_api(url_image, end_point, api_key)

            if len(all_words) > 0:
                inner_data_dict["word"] = all_words
                inner_data_dict["bounding_box"] = all_bounding_boxes
                data_dict_json[url_image] = inner_data_dict
            progress_bar.progress((url_index + 1) / num_images)

        write_json_file("data_images.json", data_dict_json)
        st.write("Finished saving the detected words ")
    return

def get_images_list(image_urls_text_file):
    request = requests.get(image_urls_text_file, verify=False)
    return request.text

def get_words_from_vision_api(url_image, end_point="cog-bbd.cognitiveservices.azure.com", api_key=None):
    headers = {
        # Request headers
        'Content-Type': 'application/json',
        'Ocp-Apim-Subscription-Key': api_key,
    }
    params = urllib.parse.urlencode({
        # Request parameters
        'language': 'unk',
        'detectOrientation': 'true',
        'model-version': 'latest',
    })
    body = {"url": url_image}

    try:
        all_words = []
        all_bounding_boxes = []
        conn = http.client.HTTPSConnection(end_point)
        conn.request("POST", "/vision/v3.2/ocr?%s" % params, f"{body}", headers)
        response = conn.getresponse()
        data_bytes = response.read()
        data_json = data_bytes.decode('utf8').replace("'", '"')
        data_json = json.loads(data_bytes)

        for item in data_json["regions"]:
            lines = item["lines"]
            for line in lines:
                words = line["words"]
                for word in words:
                    all_words.append(word["text"].lower())
                    all_bounding_boxes.append(word["boundingBox"])
        conn.close()
        return all_words, all_bounding_boxes
    except Exception as e:
        st.warning("[Errno {0}] {1}".format(e.errno, e.strerror))
    return

bs_app_modes = {
    "Search text in single image (live)" : search_text_single_image,
    "Search text in saved images data" : search_text_multi_images,
    "Detect words and save the data" : save_detected_words,
}

def main():
    mode = st.sidebar.selectbox("All modes" , list(bs_app_modes.keys()))
    bs_app_modes[mode]()

main()
