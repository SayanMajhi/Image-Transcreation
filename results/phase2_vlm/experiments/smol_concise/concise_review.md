# Concise grounded SmolVLM prompt experiment

[Original 128-token comparison](../vlm_comparison/comparison.json) | [New paired results and complete effective prompts](concise_comparison.json)

## Exact concise instruction

Describe the main subject, activity, important visible objects, and their relationships in at most four short sentences. Prioritize details essential to understanding the scene. Avoid repetition, speculation, and unsupported cultural identities. Do not describe minor background details unless they are important.

Only the eleven collection images ran, sequentially with one SmolVLM load. No Florence or sanity/warmup inference. The first concise execution is cold; original timings followed warmup. Loading and file reading are excluded from inference. CUDA peaks include resident weights, not total driver memory. The baseline is the original 128-token experiment, not the 256-token extension.

Completion is measurable; factual usefulness, repetition and cultural correctness require manual review.

## Objective completion and resource measurements

| Variant | EOS completions | Completion rate | Ceiling hits | Suspected truncations | Median ms | Peak CUDA MiB |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| original | 6/11 | 54.5% | 5 | 5 | 5617.28 | 1124.13 |
| concise | 6/11 | 54.5% | 5 | 5 | 4926.70 | 1124.16 |

EOS does not establish factual accuracy. The four-sentence request is an instruction, not an enforced stopping rule. Judge important details and repetition from the source and outputs. No repetition penalty, sampling, beam, attention or image preprocessing changes were made.

## Blank human-review worksheet

Enter Correct, Partial, Missing, Incorrect or Uncertain for each criterion after inspection. For repetition, record whether unnecessary repeated content is present and quote examples. Record unsupported claims and omissions explicitly. No model mention or source title is proof of correctness. Keep visible evidence separate from culturally specific identity judgments.

| Image | Prompt variant | Important object coverage | Relationships | Factual omissions | Unsupported claims | Repetition | Visible evidence / examples | Cultural identity / verification needed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| scene_01 | original | | | | | | | |
| scene_01 | concise_grounded | | | | | | | |
| scene_02 | original | | | | | | | |
| scene_02 | concise_grounded | | | | | | | |
| scene_03 | original | | | | | | | |
| scene_03 | concise_grounded | | | | | | | |
| scene_04 | original | | | | | | | |
| scene_04 | concise_grounded | | | | | | | |
| scene_05 | original | | | | | | | |
| scene_05 | concise_grounded | | | | | | | |
| scene_06 | original | | | | | | | |
| scene_06 | concise_grounded | | | | | | | |
| scene_07 | original | | | | | | | |
| scene_07 | concise_grounded | | | | | | | |
| scene_08 | original | | | | | | | |
| scene_08 | concise_grounded | | | | | | | |
| scene_09 | original | | | | | | | |
| scene_09 | concise_grounded | | | | | | | |
| scene_10 | original | | | | | | | |
| scene_10 | concise_grounded | | | | | | | |
| scene_11 | original | | | | | | | |
| scene_11 | concise_grounded | | | | | | | |

## scene_01

[Inspect original image](../../../../data/sample_images/durga.jpg)

Input SHA-256: `c43e0c3f07b88a310d0e120e7aa32ea5a29cecba37747015bcdec75c284e5ab0`

| Original prompt (128-token ceiling) | Concise grounded (128-token ceiling) |
| --- | --- |
| The image depicts a large, ornate, and colorful deity, likely a Hindu goddess, prominently featured in the center of the image. The deity is seated on a throne, with its arms outstretched, and is surrounded by a large, swirling, and billowing cloud of smoke. The goddess is adorned with elaborate jewelry, including a large, ornate headdress, and a richly decorated skirt. Her body is adorned with multiple arms, each holding a different object, which may represent various aspects of the goddess&#x27;s power or attributes.<br><br>The goddess is surrounded by a group of people, some of whom are holding objects, likely offerings | The image depicts a large, ornate deity with multiple arms, prominently featuring the goddess Durga. The goddess is seated on a throne and is surrounded by a large, swirling cloud of smoke. Her body is adorned with intricate patterns and jewelry, including a large, ornate headdress with multiple arms. The goddess is surrounded by a crowd of people, some of whom are holding objects resembling incense sticks, which are likely offerings to the goddess. The people are dressed in traditional Indian attire, and they are all smiling and appear to be in a festive mood.<br><br>The background includes a building with a large, white wall and a few trees |

original: tokens=128; EOS=False; ceiling=True; inference=5978.22 ms; peak CUDA bytes=1178738688.
concise: tokens=128; EOS=False; ceiling=True; inference=6714.84 ms; peak CUDA bytes=1178764288.

## scene_02

[Inspect original image](../../../../data/vlm_collection/scene_02.jpg)

Input SHA-256: `321c415a72e47d745949c90170c6342f70dafcbbe47380ff4cfaffbaf2b4dfc2`

| Original prompt (128-token ceiling) | Concise grounded (128-token ceiling) |
| --- | --- |
| In the image there are a lot of diyas placed on the floor. | In this image, there are a lot of small lights arranged on the floor. There are some coins placed on the floor. |

original: tokens=16; EOS=True; ceiling=False; inference=1103.17 ms; peak CUDA bytes=1178738688.
concise: tokens=26; EOS=True; ceiling=False; inference=1499.96 ms; peak CUDA bytes=1178764288.

## scene_03

[Inspect original image](../../../../data/vlm_collection/scene_03.jpg)

Input SHA-256: `12ad692ef221e14113160a2f1be5365dc68f316c4fe98af0deb7e1a4319f00d0`

| Original prompt (128-token ceiling) | Concise grounded (128-token ceiling) |
| --- | --- |
| A large, colorful lion costume is being worn by a group of people in a street. The costume is yellow, red, and gold, and it has a large, round head with a red nose and two large, yellow eyes. The costume has a long, curling tail, and the arms are outstretched to the sides. The people wearing the costume are standing on a street, and there are other people standing in the background. There are buildings in the background, and the sky is blue with some scattered clouds. | The image depicts a street scene featuring a large, colorful lion costume being worn by a performer. The costume is predominantly yellow with red accents, featuring intricate patterns and designs. The lion&#x27;s face is prominently featured, with large, expressive eyes and a wide, open mouth that reveals a series of sharp teeth. The costume also includes a mane that is adorned with additional red and yellow patterns.<br><br>The performer is dressed in yellow pants and red shoes, which are typical of lion dance costumes. The performer is holding a long, thin stick in their right hand, which is likely used to control the lion&#x27;s movements. The background of the |

original: tokens=106; EOS=True; ceiling=False; inference=5060.27 ms; peak CUDA bytes=1178738688.
concise: tokens=128; EOS=False; ceiling=True; inference=5812.02 ms; peak CUDA bytes=1178764288.

## scene_04

[Inspect original image](../../../../data/vlm_collection/scene_04.jpg)

Input SHA-256: `8c1b1a8880238c03d1f056a12d27d7b46e8d20bcc518b230ae105c0c977403ab`

| Original prompt (128-token ceiling) | Concise grounded (128-token ceiling) |
| --- | --- |
| A woman kneels on a table in front of a tea pot and a dish of food. There is an umbrella behind her. There are red tablecloths on the seating area. There are trees behind the seating area. | A woman kneeling on a table in front of a tea set with an umbrella. |

original: tokens=46; EOS=True; ceiling=False; inference=2342.52 ms; peak CUDA bytes=1178738688.
concise: tokens=18; EOS=True; ceiling=False; inference=1237.48 ms; peak CUDA bytes=1178764288.

## scene_05

[Inspect original image](../../../../data/vlm_collection/scene_05.jpg)

Input SHA-256: `3f38b0c2934d7e395700966b6b258de4a7fdbf613f17e6cb84758a327bbddd99`

| Original prompt (128-token ceiling) | Concise grounded (128-token ceiling) |
| --- | --- |
| The image depicts a vibrant and colorful table setup, likely intended for a festive or celebratory occasion. The table is covered with a yellow tablecloth, which is complemented by a colorful patterned drape that includes shades of purple, yellow, and red. The table is also adorned with various fruits and vegetables, arranged in a visually appealing manner.<br><br>Starting from the top, there is a framed photograph of a person, likely a family member or close friend, positioned in the center of the table. The photograph is bordered by a decorative frame, adding a touch of elegance to the setup. Below the photograph, there is a bowl filled with | The image features a vibrant and colorful table setup, adorned with various fruits and vegetables. At the center of the table is a framed photo of a person, likely a family or a significant figure, adding a personal touch to the arrangement. Surrounding the photo are an assortment of fruits, including bananas, apples, and pomegranates, all neatly arranged in a visually appealing manner.<br><br>On the table, there are also several bowls and baskets filled with fresh produce, including tomatoes, cucumbers, and leafy greens. These items are arranged in a way that suggests a variety of fresh produce, indicating a focus on healthy eating.<br><br>In the background |

original: tokens=128; EOS=False; ceiling=True; inference=7655.52 ms; peak CUDA bytes=1178738688.
concise: tokens=128; EOS=False; ceiling=True; inference=6133.02 ms; peak CUDA bytes=1178764288.

## scene_06

[Inspect original image](../../../../data/vlm_collection/scene_06.jpg)

Input SHA-256: `e0fa05019d587cc62b1d4d5a82d7440216b5d88ef0f2149a69f2eb2ee640fca0`

| Original prompt (128-token ceiling) | Concise grounded (128-token ceiling) |
| --- | --- |
| A medium outdoor shot shows a row of black doors with graffiti on them, a bicycle leaning against the sidewalk in front of the doors, and a brick sidewalk in the foreground. The doors are framed by a white wall, and the graffiti on the doors includes a blue cat, the word &quot;AGAN&quot; in white, and the word &quot;Lane&quot; in white. The bicycle is a standard two-wheeled bike with a black frame and blue seat. The sidewalk is made of red bricks, and the bricks are laid in a herringbone pattern. | A bicycle is leaning against a set of black doors. The doors are framed with white trim and have graffiti on them. The graffiti is in various colors including blue, white, yellow, and black. The bicycle is black and has a front basket. The sidewalk is made of brick and is lined with black doors. |

original: tokens=112; EOS=True; ceiling=False; inference=5617.28 ms; peak CUDA bytes=1178738688.
concise: tokens=64; EOS=True; ceiling=False; inference=3117.29 ms; peak CUDA bytes=1178764288.

## scene_07

[Inspect original image](../../../../data/vlm_collection/scene_07.jpg)

Input SHA-256: `7eabd572dd34109dffc90c4ba7a60863a01fadd2f070c77dbfe7cb88636d6d7a`

| Original prompt (128-token ceiling) | Concise grounded (128-token ceiling) |
| --- | --- |
| The image depicts a cozy, rustic interior of a traditional house. The room is dimly lit, with a warm orange hue, suggesting that it is either early morning or late afternoon. The walls are made of rough-hewn stone, giving the space a rustic and homely feel. The ceiling is made of wooden beams, adding to the rustic charm of the room.<br><br>In the center of the room, there is a small, round, glowing fire pit. The fire pit is surrounded by a few items: a few metal pots and pans, a small bowl, and a few other objects that appear to be cooking utensils. | The image depicts a cozy, traditional living space. The room is constructed with earthy tones, primarily red, orange, and brown, giving it a warm and inviting atmosphere. The walls are made of rough-hewn stones, and the ceiling is constructed from wooden beams. The room features a thatched roof, which adds to the rustic charm of the space.<br><br>In the center of the room, there is a small, round, glowing fire pit. The fire pit is surrounded by a mat, and a few items are placed around it, including a bowl, a ladle, and a few other cooking utensils. The fire is |

original: tokens=128; EOS=False; ceiling=True; inference=6192.10 ms; peak CUDA bytes=1178738688.
concise: tokens=128; EOS=False; ceiling=True; inference=6220.57 ms; peak CUDA bytes=1178764288.

## scene_08

[Inspect original image](../../../../data/vlm_collection/scene_08.jpg)

Input SHA-256: `249a8c34530c2c5d68d266372b787401e2197bc0e8faa0b57b21735082e1fa1c`

| Original prompt (128-token ceiling) | Concise grounded (128-token ceiling) |
| --- | --- |
| In an outdoor setting, a group of young men are playing soccer on a stone-paved area. One of the players is in a blue shirt with the number 38 on the back. The player is stretching out his body with one arm extended towards the ball. Another player is in a white shirt with a blue and black graphic on the back. The player in the white shirt is looking at the player in the blue shirt. The player in the blue shirt is looking at the ball. The player in the white shirt has his arms extended out to the sides. The player in the blue shirt has his arms extended out to the | In an outdoor setting, a group of young men are playing soccer. One of them is wearing a blue shirt with the number 38 on the back. The other players are in various poses, some stretching, others running. In the background, there is a brick wall and several other people standing and walking. |

original: tokens=128; EOS=False; ceiling=True; inference=6218.50 ms; peak CUDA bytes=1178738688.
concise: tokens=64; EOS=True; ceiling=False; inference=3148.57 ms; peak CUDA bytes=1178764288.

## scene_09

[Inspect original image](../../../../data/vlm_collection/scene_09.jpg)

Input SHA-256: `91348a0926e75d082f6298d13db9fb82b2a6d6934ecbd5d52b2cb16854db119a`

| Original prompt (128-token ceiling) | Concise grounded (128-token ceiling) |
| --- | --- |
| The image depicts a scene of a kitchen or cooking area. The primary objects in the image include:<br><br>1. **People**: There are three individuals in the image. <br>   - **Person in the Front**: This person is standing and appears to be holding a large bowl or container. The person is wearing a long, dark-colored garment, possibly a skirt or a long coat.<br>   - **Person Behind the Person in the Front**: This person is standing behind the person in the front. They are wearing a light-colored garment, possibly a shirt or a jacket.<br>   - **Person Behind the Person Behind the Person**: This | A painting of a kitchen scene. There are three women in the kitchen. One woman is holding a bowl. |

original: tokens=128; EOS=False; ceiling=True; inference=6743.70 ms; peak CUDA bytes=1178738688.
concise: tokens=23; EOS=True; ceiling=False; inference=1407.29 ms; peak CUDA bytes=1178764288.

## scene_10

[Inspect original image](../../../../data/vlm_collection/scene_10.jpg)

Input SHA-256: `2fb7febc73bf3113266c6ff2a0fe21159efa440f6dee8c858b2c72ef6a375643`

| Original prompt (128-token ceiling) | Concise grounded (128-token ceiling) |
| --- | --- |
| An aerial shot of the Netherlands. The river IJsselmeer is on the left side of the image, and the IJsselmeer is on the right side. The IJsselmeer is a large river that flows from the North Sea to the South Sea. The Netherlands is a country in Western Europe. The Netherlands is known for its canals. The canals are a major feature of the Netherlands. The Netherlands is a country that is known for its architecture. The architecture is a mix of Dutch and European styles. | An aerial shot of the Netherlands, showing the IJ (the most important river in the country) and the IJsselmeer (the second most important river). The IJ is a narrow strip of water between the Netherlands and Belgium. The IJsselmeer is a large river that flows through the center of the country. The Netherlands is a country in Europe, and the IJsselmeer is a major river in the country. |

original: tokens=111; EOS=True; ceiling=False; inference=5299.93 ms; peak CUDA bytes=1178738688.
concise: tokens=95; EOS=True; ceiling=False; inference=4926.70 ms; peak CUDA bytes=1178764288.

## scene_11

[Inspect original image](../../../../data/vlm_collection/scene_11.jpg)

Input SHA-256: `3dae75e7e6274c66ed235f4cc675dd71c949d3d198debd24c8628984daa7ec7d`

| Original prompt (128-token ceiling) | Concise grounded (128-token ceiling) |
| --- | --- |
| A train station with two trains parked facing away from the viewer. The train on the right is a blue train with a red sign on top of it. The train on the left is a white train with a blue stripe along the side. There is a pole in the foreground with a sign on it that says &quot;1&quot;. There is snow on the ground. The sky is dark with a thick, dark cloud above the station. | The scene depicts a snowy train station at night. The station is equipped with a red light, indicating that it is operational. The ground is covered in snow, and the tracks are empty. There are two trains parked at the station, both of which are blue. The train on the left is a double-decker, while the one on the right is a single-decker. Both trains have their headlights on, suggesting that they are either at a stop or in motion.<br><br>Above the station, the sky is dark, and there are clouds, which are typical for a night scene. The lighting is sufficient to illuminate |

original: tokens=87; EOS=True; ceiling=False; inference=4192.09 ms; peak CUDA bytes=1178738688.
concise: tokens=128; EOS=False; ceiling=True; inference=6137.16 ms; peak CUDA bytes=1178764288.

Reviewer: __________  Date: __________

Manual model-selection conclusion: __________
