import os, subprocess
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import attr
import enlighten
import InquirerPy
from fpdf import FPDF

from src.constants import THREADS, States
from src.order import CardOrder
from src.processing import ImagePostProcessingConfig
from src.utils import bold


@attr.s
class PdfExporter:
    order: CardOrder = attr.ib(default=attr.Factory(CardOrder.from_xml_in_folder))
    state: str = attr.ib(init=False, default=States.initialising)
    pdf: FPDF = attr.ib(default=None)
    card_width_in_inches: float = attr.ib(default=2.73)
    card_height_in_inches: float = attr.ib(default=3.71)
    file_num: int = attr.ib(default=1)
    number_of_cards_per_file: int = attr.ib(default=60)
    paths_by_slot: dict[int, tuple[str, str]] = attr.ib(default={})
    save_path: str = attr.ib(default="")
    separate_faces: bool = attr.ib(default=False)
    current_face: str = attr.ib(default="all")
    manager: enlighten.Manager = attr.ib(init=False, default=attr.Factory(enlighten.get_manager))
    status_bar: enlighten.StatusBar = attr.ib(init=False, default=False)
    download_bar: enlighten.Counter = attr.ib(init=False, default=None)
    processed_bar: enlighten.Counter = attr.ib(init=False, default=None)

    def configure_bars(self) -> None:
        num_images = len(self.order.fronts.cards) + len(self.order.backs.cards)
        status_format = "State: {state}"
        self.status_bar = self.manager.status_bar(
            status_format=status_format,
            state=f"{bold(self.state)}",
            position=1,
        )
        self.download_bar = self.manager.counter(total=num_images, desc="Images Downloaded", position=2)
        self.processed_bar = self.manager.counter(total=num_images, desc="Images Processed", position=3)

        self.download_bar.refresh()
        self.processed_bar.refresh()

    def set_state(self, state: str) -> None:
        self.state = state
        self.status_bar.update(state=f"{bold(self.state)}")
        self.status_bar.refresh()

    def __attrs_post_init__(self) -> None:
        self.ask_questions()
        self.configure_bars()
        self.generate_file_path()

    def ask_questions(self) -> None:
        questions = [
            {
                "type": "list",
                "name": "split_faces",
                "message": "Do you want the front and back of the cards in separate PDFs? (required for MPC).",
                "default": 0,
                "choices": [
                    InquirerPy.base.control.Choice(False, name="No"),
                    InquirerPy.base.control.Choice(True, name="Yes"),
                ],
            },
            {
                "type": "number",
                "name": "cards_per_file",
                "message": "How many cards should be included in the generated files? Note: The more cards per file, "
                + "the longer the processing will take and the larger the file size will be.",
                "default": 60,
                "when": lambda result: result["split_faces"] is False,
                "transformer": lambda result: 1 if (int_result := int(result)) < 1 else int_result,
            },
        ]
        answers = InquirerPy.prompt(questions)
        if answers["split_faces"]:
            self.separate_faces = True
            self.number_of_cards_per_file = 1
        else:
            self.number_of_cards_per_file = (
                1 if (int_cards_per_file := int(answers["cards_per_file"])) < 1 else int_cards_per_file
            )

    def generate_file_path(self) -> None:
        basename = os.path.basename(str(self.order.name))
        if not basename:
            basename = "cards.xml"
        file_name = os.path.splitext(basename)[0]
        self.save_path = f"export/{file_name}/"
        os.makedirs(self.save_path, exist_ok=True)
        if self.separate_faces:
            for face in ["backs", "fronts"]:
                os.makedirs(self.save_path + face, exist_ok=True)

    def generate_pdf(self) -> None:
        pdf = FPDF("P", "in", (self.card_width_in_inches, self.card_height_in_inches))
        self.pdf = pdf
        
    def generate_pdf_a3(self) -> None:
        pdf = FPDF(orientation='L', format='A3')
        self.pdf = pdf

    def add_image(self, image_path: str) -> None:
        self.pdf.add_page()
        self.pdf.image(image_path, x=0, y=0, w=self.card_width_in_inches, h=self.card_height_in_inches)

    def save_file(self) -> None:
        extra = ""
        if self.separate_faces:
            extra = f"{self.current_face}/"
        self.pdf.output(f"{self.save_path}{self.file_num}.pdf")

    def download_and_collect_images(self, post_processing_config: Optional[ImagePostProcessingConfig]) -> None:
        with ThreadPoolExecutor(max_workers=THREADS) as pool:
            self.order.fronts.download_images(pool, self.download_bar, post_processing_config)
            self.order.backs.download_images(pool, self.download_bar, post_processing_config)

        backs_by_slots = {}
        for card in self.order.backs.cards:
            for slot in card.slots:
                backs_by_slots[slot] = card.file_path

        fronts_by_slots = {}
        for card in self.order.fronts.cards:
            for slot in card.slots:
                fronts_by_slots[slot] = card.file_path

        paths_by_slot = {}
        for slot in fronts_by_slots.keys():
            paths_by_slot[slot] = (str(backs_by_slots.get(slot, backs_by_slots[0])), str(fronts_by_slots[slot]))
        self.paths_by_slot = paths_by_slot

    def execute(self, post_processing_config: Optional[ImagePostProcessingConfig]) -> None:
        self.download_and_collect_images(post_processing_config=post_processing_config)
        if self.separate_faces:
            self.number_of_cards_per_file = 1
            self.prepare_images()
            self.export_a3()
            # self.export_separate_faces()
        else:
            self.export()

        print(f"Finished exporting files! They should be accessible at {self.save_path}.")

    def export(self) -> None:
        for slot in sorted(self.paths_by_slot.keys()):
            (back_path, front_path) = self.paths_by_slot[slot]
            self.set_state(f"Working on slot {slot}")
            if slot == 0:
                self.generate_pdf()
            elif slot % self.number_of_cards_per_file == 0:
                self.set_state(f"Saving PDF #{slot}")
                self.save_file()
                self.file_num = self.file_num + 1
                self.generate_pdf()
            self.set_state(f"Adding images for slot {slot}")
            self.add_image(back_path)
            self.add_image(front_path)
            self.processed_bar.update()

        self.set_state(f"Saving PDF #{self.file_num}")
        self.save_file()

    def export_separate_faces(self) -> None:
        all_faces = ["backs", "fronts"]
        for slot in sorted(self.paths_by_slot.keys()):
            image_paths_tuple = self.paths_by_slot[slot]
            self.set_state(f"Working on slot {slot}")
            for face in all_faces:
                face_index = all_faces.index(face)
                self.current_face = face
                self.generate_pdf()
                self.add_image(image_paths_tuple[face_index])
                self.set_state(f"Saving {face} PDF for slot {slot}")
                self.save_file()
                if face_index == 1:
                    self.file_num = self.file_num + 1
    
    def export_a3(self):
        line_w = 0.14
        line_lv = 297
        line_lh = 440
        image_w = 63
        image_h = 88
        top = 15
        left = 20
        gap = 0.5

        # create pdf in a3 format
        self.generate_pdf_a3()
        self.add_a3_page()

        i = 0        
        # iterate over pages adding images
        for slot in sorted(self.paths_by_slot.keys()):
            image_paths_tuple = self.paths_by_slot[slot]
            self.set_state(f"Working on slot {slot}")

            if i > 0 and i % 18 == 0:
                self.add_a3_page()

            # calculate position relative to card index and position on a page
            # page contains 3 rows of 6 cards
            x = left + (i % 6) * image_w + (i % 6) * gap
            y = top + int(i / 6 % 3) * image_h + int(i / 6 % 3) * gap
            
            # add image
            self.pdf.image(
                image_paths_tuple[1],
                x=x,
                y=y,
                w=image_w,
                h=image_h,
            )
            i += 1
        # done adding pages and images
        self.save_file()

    def add_a3_page(self):
        
        line_w = 0.14
        line_lv = 297
        line_lh = 440
        image_w = 63
        image_h = 88
        top = 15
        left = 20
        gap = 0.5


        self.pdf.add_page()
        # add page, add lines
        # DRAW SIDE CUT LINES
        # left
        self.pdf.dashed_line(left - line_w, 0, left - line_w, line_lv, 1, 2)
        # right
        self.pdf.dashed_line(
            left + (image_w * 6) + gap * 5 + 0.1,
            0,
            left + (image_w * 6) + gap * 5 + 0.1,
            line_lv,
            1,
            2,
        )
        # top
        self.pdf.dashed_line(0, top - line_w, line_lh, top - line_w, 1, 2)
        # bottom
        self.pdf.dashed_line(
            0,
            top + image_h * 3 + gap * 2 + 0.1,
            line_lh,
            top + image_h * 3 + gap * 2 + 0.1,
            1,
            2,
        )
    
        # draw vertical lines between cards
        for i in range(1, 6):
            # draw 2 lines for easier cutting
            self.pdf.dashed_line(
                left + image_w * i + gap * (i-1) + 0.1,
                0,
                left + image_w * i + gap * (i-1) + 0.1,
                line_lv,
                1,
                2,
            )
            self.pdf.dashed_line(
                left + image_w * i + gap * (i-1) + gap - line_w,
                0,
                left + image_w * i + gap * (i-1) + gap - line_w,
                line_lv,
                1,
                2,
            )
    
        # draw horizontal lines between cards
        for i in range(1, 3):
            # draw 2 lines for easier cutting
            self.pdf.dashed_line(
                0, top + image_h * i + gap * (i-1) + 0.1, line_lh, top + image_h * i + gap * (i-1) + 0.1, 1, 2
            )
            self.pdf.dashed_line(
                0,
                top + image_h * i + gap * (i-1) + gap - line_w,
                line_lh,
                top + image_h * i + gap * (i-1) + gap - line_w,
                1,
                2,
            )
    # end add_a3_page
                    
    def prepare_images(self) -> None:
        print('preparing images')
        for slot in self.paths_by_slot.keys():
            front_back_image_tuple = self.paths_by_slot[slot]
            # convert image to jpg if it's not
            jpeg_path = self.convert_to_jpg(front_back_image_tuple[1])
            # re-set image back into paths
            self.paths_by_slot[slot] = (front_back_image_tuple[0], jpeg_path)
            
            need_downsize = 0
            need_reshape = 1
            need_compression = 2
            preparadness_check_result = self.images_havent_been_prepared(jpeg_path)
            if (preparadness_check_result[need_compression]):
                # compress before downsizing - it will preserve better quality
                # compress image to reduce it's size
                self.compress_image(jpeg_path)
            if (preparadness_check_result[need_reshape]):
                # cut sides of the image to reduce border size
                self.cut_and_reshape(jpeg_path)
            if (preparadness_check_result[need_downsize]):
                # resize image to reduce it's size
                self.downsize_image(jpeg_path)

# convert image to jpg -- update the image name (stored)
    def convert_to_jpg(self, image_path: str) -> None:
        if image_path.endswith('jpg'):
            return image_path
        jpeg_path = self.new_jpg_path(image_path)
        if os.path.exists(jpeg_path): # if jpg was previously processed and exists, skip ceation of jpg
            return jpeg_path
        print('converting to jpg')
        command = f'magick "{image_path}" "{jpeg_path}"'
        subprocess.run(command, shell=True, capture_output=False, text=False)
        return jpeg_path

    def new_jpg_path(self, image_path) -> None:
        last_dot_index = image_path.rfind(".")
        return image_path[:last_dot_index] + ".jpg"

    def compress_image(self, jpeg_path: str) -> None:
        print('compressing image')
        command = f'magick "{jpeg_path}" -strip -interlace Plane -gaussian-blur 0.05 -quality 85% "{jpeg_path}"'
        subprocess.run(command, shell=True, capture_output=False, text=False)

    def downsize_image(self, jpeg_path: str) -> None:
        print('resizint image')
        command = f'mogrify -resize "60%" "{jpeg_path}"'
        subprocess.run(command, shell=True, capture_output=False, text=False)
       
    def cut_and_reshape(self, jpeg_path: str) -> None:
        print('cutting corners')
        command = f'mogrify -shave "2.8%x2.8%" -gravity center -crop "63:88" "{jpeg_path}"'
        subprocess.run(command, shell=True, capture_output=False, text=False)

    def images_havent_been_prepared(self, jpeg_path):
        command = f'identify -verbose "{jpeg_path}"'
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        output = str(result.stdout)
        # print(output)
        # if amount of pixels is too large - crop and downsize
        output = output.splitlines()
        need_downsize = False
        need_reshape = True
        need_compression = False
        for line in output:
            if "Geometry" in line:
                w, h = line.strip().split(" ")[1].split("+")[0].split("x")
                w = int(w)
                h = int(h)
                # check size is lower than large x and y - if not, downsize by certain percentage - calculate the percentage
                # if w < 1020 and h < 1500:
                #     need_downsize = False
                # check shape is of certain relationship to each other, if not - need reshape
                w_rel = round(w/63, 1)
                h_rel = round(h/88, 1)
                if w_rel == h_rel: 
                    need_reshape = False
            # elif "Quality: " in line:
            #     # check compression
            #     quality = int(line.strip().split(" ")[1])
            #     if quality <= 85:
            #         need_compression = False
        return [need_downsize, need_reshape, need_compression]
