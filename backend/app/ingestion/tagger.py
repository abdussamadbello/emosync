class CBTTagger:
    def tag(self, text: str):
        tags = []

        text_lower = text.lower()

        if "negative thought" in text_lower:
            tags.append("negative_thoughts")

        if "cognitive distortion" in text_lower:
            tags.append("cognitive_distortion")

        if "behavior" in text_lower:
            tags.append("behavior_pattern")

        if "emotion" in text_lower:
            tags.append("emotional_regulation")

        return {
            "source": "cbt_pdf",
            "tags": tags
        }