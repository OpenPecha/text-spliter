from pathlib import Path


from openpecha.serializers.hfml import HFMLSerializer


def get_text(text_id, opf_path, output_dir):
    hfml_serializer = HFMLSerializer(opf_path, text_id, layers=[])
    hfml_serializer.serialize(output_dir, text_id)

if __name__ == "__main__":
    text_ids = Path('./data/text_list.txt').read_text(encoding='utf-8').splitlines()
    for text_id in text_ids:
        opf_path = './data/P000002.opf'
        output_dir = Path(f'./data/text/{text_id}')
        output_dir.mkdir(exist_ok=True, parents=True)
        try:
            get_text(text_id, opf_path, output_dir)
        except:
            output_dir.rmdir()
            print(f'{text_id} failed')
