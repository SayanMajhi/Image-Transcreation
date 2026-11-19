# Updated blank model-selection worksheet

[Original results](../vlm_comparison/comparison.json) | [Original blank worksheet](../vlm_comparison/review.md) | [128 vs 256 comparison](truncation_comparison.md) | [Extended JSON](smol_extended.json)

Use the latest EOS-complete SmolVLM caption where available; the six completed original SmolVLM captions and every Florence caption are retained without inference. If an extended caption lacks EOS, it is explicitly unresolved, not presented as complete.

Only the five selected images ran; no Florence, completed SmolVLM or sanity/warmup inference. The first extended inference is cold; original collection timings followed warmup. Loading is excluded from inference; CUDA allocated peaks include resident weights. The assembled worksheet mixes retained 128-token results and selective 256-token reruns.

The original convenience-sample, prompt-format, preprocessing and decoding differences still apply. The selective extension changes only SmolVLM's token ceiling for five images. Neither text length nor EOS is an accuracy score.

All scores remain blank. Coverage/relationships: 0 poor, 1 limited, 2 mostly correct, 3 strong visible support. Omissions: 0 severe, 1 several, 2 minor, 3 none observed. Hallucinations: 0 severe, 1 several unsupported claims, 2 minor, 3 none observed. Use N/A or Uncertain where appropriate. Keep culturally specific identity judgments separate from visible object recognition and record evidence for each claim.

| Image | Model | Coverage 0-3 | Relationships 0-3 | Omissions 0-3 | Hallucinations 0-3 | Visible evidence | Cultural identity / verification needed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| scene_01 | smolvlm | | | | | | |
| scene_01 | florence | | | | | | |
| scene_02 | smolvlm | | | | | | |
| scene_02 | florence | | | | | | |
| scene_03 | smolvlm | | | | | | |
| scene_03 | florence | | | | | | |
| scene_04 | smolvlm | | | | | | |
| scene_04 | florence | | | | | | |
| scene_05 | smolvlm | | | | | | |
| scene_05 | florence | | | | | | |
| scene_06 | smolvlm | | | | | | |
| scene_06 | florence | | | | | | |
| scene_07 | smolvlm | | | | | | |
| scene_07 | florence | | | | | | |
| scene_08 | smolvlm | | | | | | |
| scene_08 | florence | | | | | | |
| scene_09 | smolvlm | | | | | | |
| scene_09 | florence | | | | | | |
| scene_10 | smolvlm | | | | | | |
| scene_10 | florence | | | | | | |
| scene_11 | smolvlm | | | | | | |
| scene_11 | florence | | | | | | |

## scene_01

[Inspect source image](../../../../data/sample_images/durga.jpg)

SmolVLM source: **extended_256**; status: **unresolved_no_complete_caption**.

**SmolVLM:** The image depicts a large, ornate, and colorful deity, likely a Hindu goddess, prominently featured in the center of the image. The deity is seated on a throne, with its arms outstretched, and is surrounded by a large, swirling, and billowing cloud of smoke. The goddess is adorned with elaborate jewelry, including a large, ornate headdress, and a richly decorated skirt. Her body is adorned with multiple arms, each holding a different object, which may represent various aspects of the goddess&#x27;s power or attributes.

The goddess is surrounded by a group of people, some of whom are holding objects, likely offerings or incense sticks, in their hands. These objects are placed on a platform or a large, flat surface, which may be a stage or a platform for the goddess&#x27;s worship. The people are dressed in traditional Indian attire, which includes long, colorful saris.

In the background, there are trees and what appears to be a building or a structure, suggesting that the scene is taking place in a temple or a sacred site. The sky is partially visible, with some clouds, indicating that the scene is likely taking place during a religious or cultural event.

The image conveys a sense of reverence and devotion, as the people

**Florence (unchanged original):** A group of women are dancing together. They are all dressed in traditional Indian garb. One of the women is in the middle of the group dancing. She is wearing a colorful garb and headdress. The women are holding brown bowls in their hands. There is smoke coming out of the bowls. There are wires hanging above the women.

[Original captions and measurements](../vlm_comparison/comparison.json)

## scene_02

[Inspect source image](../../../../data/vlm_collection/scene_02.jpg)

SmolVLM source: **original_128**; status: **complete_eos**.

**SmolVLM:** In the image there are a lot of diyas placed on the floor.

**Florence (unchanged original):** There are several small candles on the ground. There are small white rocks under the candles. There is a small gold bowl in the middle of the rocks.

[Original captions and measurements](../vlm_comparison/comparison.json)

## scene_03

[Inspect source image](../../../../data/vlm_collection/scene_03.jpg)

SmolVLM source: **original_128**; status: **complete_eos**.

**SmolVLM:** A large, colorful lion costume is being worn by a group of people in a street. The costume is yellow, red, and gold, and it has a large, round head with a red nose and two large, yellow eyes. The costume has a long, curling tail, and the arms are outstretched to the sides. The people wearing the costume are standing on a street, and there are other people standing in the background. There are buildings in the background, and the sky is blue with some scattered clouds.

**Florence (unchanged original):** There is a person in a large yellow and red costume. They are standing in the middle of the street. There are people standing behind them watching them.

[Original captions and measurements](../vlm_comparison/comparison.json)

## scene_04

[Inspect source image](../../../../data/vlm_collection/scene_04.jpg)

SmolVLM source: **original_128**; status: **complete_eos**.

**SmolVLM:** A woman kneels on a table in front of a tea pot and a dish of food. There is an umbrella behind her. There are red tablecloths on the seating area. There are trees behind the seating area.

**Florence (unchanged original):** A woman is wearing a brown dress. She is sitting in front of a table. There is a red umbrella over the table.

[Original captions and measurements](../vlm_comparison/comparison.json)

## scene_05

[Inspect source image](../../../../data/vlm_collection/scene_05.jpg)

SmolVLM source: **extended_256**; status: **unresolved_no_complete_caption**.

**SmolVLM:** The image depicts a vibrant and colorful table setup, likely intended for a festive or celebratory occasion. The table is covered with a yellow tablecloth, which is complemented by a colorful patterned drape that includes shades of purple, yellow, and red. The table is also adorned with various fruits and vegetables, arranged in a visually appealing manner.

Starting from the top, there is a framed photograph of a person, likely a family member or close friend, positioned in the center of the table. The photograph is bordered by a decorative frame, adding a touch of elegance to the setup. Below the photograph, there is a bowl filled with fresh apples, which are likely part of the fruit selection.

To the left of the bowl, there is a basket containing a variety of fruits, including bananas, apples, and possibly other types of produce. The bananas are prominently displayed, and they are accompanied by a small bowl filled with a green leafy vegetable, possibly a type of lettuce or spinach.

To the right of the bowl, there is a bowl filled with a variety of fruits, including bananas, apples, and possibly other types of produce. The bowl is also adorned with a decorative element, possibly a flower or a small plant, adding a touch of nature to

**Florence (unchanged original):** There is a table with a yellow table cloth on it. There is a picture hanging on the wall behind the table. There are flowers in vases on the table in front of the flowers.

[Original captions and measurements](../vlm_comparison/comparison.json)

## scene_06

[Inspect source image](../../../../data/vlm_collection/scene_06.jpg)

SmolVLM source: **original_128**; status: **complete_eos**.

**SmolVLM:** A medium outdoor shot shows a row of black doors with graffiti on them, a bicycle leaning against the sidewalk in front of the doors, and a brick sidewalk in the foreground. The doors are framed by a white wall, and the graffiti on the doors includes a blue cat, the word &quot;AGAN&quot; in white, and the word &quot;Lane&quot; in white. The bicycle is a standard two-wheeled bike with a black frame and blue seat. The sidewalk is made of red bricks, and the bricks are laid in a herringbone pattern.

**Florence (unchanged original):** A bicycle is parked in front of a building. The building is covered in graffiti. The graffiti is colorful. There are three doors on the building.

[Original captions and measurements](../vlm_comparison/comparison.json)

## scene_07

[Inspect source image](../../../../data/vlm_collection/scene_07.jpg)

SmolVLM source: **extended_256**; status: **unresolved_no_complete_caption**.

**SmolVLM:** The image depicts a cozy, rustic interior of a traditional house. The room is dimly lit, with a warm orange hue, suggesting that it is either early morning or late afternoon. The walls are made of rough-hewn stone, giving the space a rustic and homely feel. The ceiling is made of wooden beams, adding to the rustic charm of the room.

In the center of the room, there is a small, round, glowing fire pit. The fire pit is surrounded by a few items: a few metal pots and pans, a small bowl, and a few other objects that appear to be cooking utensils. The fire is small, and it is not actively burning, indicating that it is not the primary source of heat for the room.

To the right of the fire pit, there is a woman seated on a raised platform. She is wearing a traditional outfit, which includes a long, loose-fitting garment with a patterned design and a headscarf. The woman is engaged in a ritual or activity, possibly cooking or preparing food. She is holding a long, thin cooking utensil, which appears to be a ladle or a spoon, and is stirring or stirring something in a pot or pan.

The room is furnished

**Florence (unchanged original):** A man is sitting in front of a fire. The man is wearing a checkered shirt. There is a shelf above the man with utensils on it.

[Original captions and measurements](../vlm_comparison/comparison.json)

## scene_08

[Inspect source image](../../../../data/vlm_collection/scene_08.jpg)

SmolVLM source: **extended_256**; status: **unresolved_no_complete_caption**.

**SmolVLM:** In an outdoor setting, a group of young men are playing soccer on a stone-paved area. One of the players is in a blue shirt with the number 38 on the back. The player is stretching out his body with one arm extended towards the ball. Another player is in a white shirt with a blue and black graphic on the back. The player in the white shirt is looking at the player in the blue shirt. The player in the blue shirt is looking at the ball. The player in the white shirt has his arms extended out to the sides. The player in the blue shirt has his arms extended out to the sides. The player in the white shirt has his arms extended out to the sides. The player in the blue shirt has his arms extended out to the sides. The player in the white shirt has his arms extended out to the sides. The player in the blue shirt has his arms extended out to the sides. The player in the white shirt has his arms extended out to the sides. The player in the blue shirt has his arms extended out to the sides. The player in the white shirt has his arms extended out to the sides. The player in the blue shirt has his arms extended out to the sides. The player in the white shirt

**Florence (unchanged original):** A group of boys are playing soccer outside on a sunny day. Two of the boys are wearing blue shirts and shorts. One boy is laying on the ground trying to kick the ball. A group of people can be seen standing on a sidewalk behind the boys. A tall brick building is standing near the people.

[Original captions and measurements](../vlm_comparison/comparison.json)

## scene_09

[Inspect source image](../../../../data/vlm_collection/scene_09.jpg)

SmolVLM source: **extended_256**; status: **unresolved_no_complete_caption**.

**SmolVLM:** The image depicts a scene of a kitchen or cooking area. The primary objects in the image include:

1. **People**: There are three individuals in the image. 
   - **Person in the Front**: This person is standing and appears to be holding a large bowl or container. The person is wearing a long, dark-colored garment, possibly a skirt or a long coat.
   - **Person Behind the Person in the Front**: This person is standing behind the person in the front. They are wearing a light-colored garment, possibly a shirt or a jacket.
   - **Person Behind the Person Behind the Person**: This person is standing behind the person in the back. They are wearing a dark-colored garment, possibly a coat or a sweater.

2. **Cooking Area**:
   - **Table**: In the foreground, there is a table with various items on it. The table is covered with a white cloth.
   - **Baskets**: There are two baskets on the table. One basket is filled with food items, possibly bread or other types of bread. The other basket is empty.
   - **Cooking Tools**: There are some cooking tools on the table, including a large knife and a bowl.

3. **

**Florence (unchanged original):** A painting of people standing around a table. There are baskets on the table in front of them. There is a woman in a red dress standing next to the table.

[Original captions and measurements](../vlm_comparison/comparison.json)

## scene_10

[Inspect source image](../../../../data/vlm_collection/scene_10.jpg)

SmolVLM source: **original_128**; status: **complete_eos**.

**SmolVLM:** An aerial shot of the Netherlands. The river IJsselmeer is on the left side of the image, and the IJsselmeer is on the right side. The IJsselmeer is a large river that flows from the North Sea to the South Sea. The Netherlands is a country in Western Europe. The Netherlands is known for its canals. The canals are a major feature of the Netherlands. The Netherlands is a country that is known for its architecture. The architecture is a mix of Dutch and European styles.

**Florence (unchanged original):** This is an aerial view of a city. The sky is blue with white fluffy clouds. The water is blue and calm. The land is brown. There are many buildings and houses on the land.

[Original captions and measurements](../vlm_comparison/comparison.json)

## scene_11

[Inspect source image](../../../../data/vlm_collection/scene_11.jpg)

SmolVLM source: **original_128**; status: **complete_eos**.

**SmolVLM:** A train station with two trains parked facing away from the viewer. The train on the right is a blue train with a red sign on top of it. The train on the left is a white train with a blue stripe along the side. There is a pole in the foreground with a sign on it that says &quot;1&quot;. There is snow on the ground. The sky is dark with a thick, dark cloud above the station.

**Florence (unchanged original):** Two blue and white trains are parked at a train station at night. There is a light pole in front of the platform with a sign on it.

[Original captions and measurements](../vlm_comparison/comparison.json)

Reviewer: __________  Date: __________

Manual model-selection conclusion: __________
