"""
Utilities for generating the clinical report from an image using the emotion model.
Used by the Streamlit UI. Model should be saved from image_model.ipynb first.
"""
import os
import datetime
import numpy as np

# Default class names (same order as in notebook's dataset)
DEFAULT_CLASS_NAMES = [
    "angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"
]

_REPORT_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_PATH = os.path.join(_REPORT_DIR, "clinical_report.txt")
# Prefer SavedModel (directory) for cross-version compatibility; fallback to .keras
MODEL_PATH_SAVEDMODEL = os.path.join(_REPORT_DIR, "emotion_model")
MODEL_PATH_KERAS = os.path.join(_REPORT_DIR, "emotion_model.keras")


def load_and_preprocess_image(image_bytes_or_path, size=(48, 48)):
    """Load image from bytes or path and preprocess to 48x48 grayscale for model."""
    try:
        from PIL import Image
        import io
    except ImportError:
        raise ImportError("PIL (Pillow) is required. Install with: pip install Pillow")

    if isinstance(image_bytes_or_path, bytes):
        img = Image.open(io.BytesIO(image_bytes_or_path))
    else:
        img = Image.open(image_bytes_or_path)

    img = img.convert("L")  # grayscale
    img = img.resize(size, Image.Resampling.LANCZOS)
    arr = np.array(img, dtype=np.float32)
    # Model expects (48, 48, 1), values will be rescaled by model's Rescaling layer
    arr = np.expand_dims(arr, axis=-1)
    return arr


def generate_report_text(image_array, model, class_names, student_id="Student_001"):
    """Generate the clinical report text (same logic as in image_model.ipynb)."""
    img_array = np.expand_dims(image_array, axis=0)
    predictions = model.predict(img_array, verbose=0)[0]
    pred_index = int(np.argmax(predictions))
    confidence = float(predictions[pred_index])
    emotion = class_names[pred_index].strip().lower()

    top3_idx = predictions.argsort()[-3:][::-1]
    top3 = [(class_names[i], float(predictions[i])) for i in top3_idx]

    emotion_reasoning = {
        "angry": [
            "Eyebrow contraction detected, suggesting a frowning pattern",
            "Mouth region shows tension consistent with anger/frustration",
            "Overall facial muscle tightness appears higher than neutral expressions",
        ],
        "sad": [
            "Mouth curvature appears reduced or downward",
            "Eye region appears less activated than positive expressions",
            "Facial expression looks less dynamic, which can align with sadness",
        ],
        "fear": [
            "Eye region appears widened compared with neutral expressions",
            "Eyebrow shape suggests raised tension",
            "Facial pattern indicates alertness or discomfort",
        ],
        "happy": [
            "Mouth corners appear raised, suggesting a smile pattern",
            "Cheek region appears more active",
            "Overall expression is more relaxed and positive",
        ],
        "neutral": [
            "Facial muscles appear balanced without a strong emotional signal",
            "No dominant activation in mouth or eyebrow regions",
            "Expression is relatively stable and non-exaggerated",
        ],
        "surprise": [
            "Eye region appears widened",
            "Eyebrows may be raised",
            "Expression suggests a sudden emotional response",
        ],
        "disgust": [
            "Upper mouth region appears tense",
            "Facial contraction suggests aversion",
            "Expression differs from neutral with localized tension",
        ],
    }

    observed_patterns = emotion_reasoning.get(
        emotion,
        ["The model detected a general facial pattern associated with this class."],
    )

    if confidence >= 0.75:
        confidence_note = "High confidence prediction"
    elif confidence >= 0.50:
        confidence_note = "Moderate confidence prediction"
    else:
        confidence_note = "Low confidence prediction; the model is somewhat uncertain"

    interpretation_map = {
        "sad": "This may reflect low mood or depressive affect.",
        "fear": "This may reflect anxiety, worry, or discomfort.",
        "angry": "This may reflect frustration, stress, or emotional tension.",
        "neutral": "This suggests no strong visible emotional activation at this moment.",
        "happy": "This suggests a positive visible emotional state.",
        "surprise": "This suggests a brief reactive emotional state.",
        "disgust": "This suggests a negative affective reaction.",
    }
    interpretation = interpretation_map.get(
        emotion, "This reflects the model's detected emotional class."
    )

    lines = []
    lines.append("=" * 66)
    lines.append("AI-ASSISTED MENTAL HEALTH SCREENING REPORT")
    lines.append("=" * 66)
    lines.append("")
    lines.append(f"Student ID: {student_id}")
    lines.append(f"Analysis Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append("-" * 63)
    lines.append("MODEL PREDICTION")
    lines.append("-" * 63)
    lines.append("")
    lines.append(f"Primary Emotion Detected: {emotion.upper()}")
    lines.append(f"Confidence Score: {confidence:.2%}")
    lines.append(f"Interpretation: {confidence_note}")
    lines.append("")
    lines.append("Model also considered:")
    lines.append("")
    for e, p in top3:
        lines.append(f"  • {e.capitalize():10s} : {p:.2%}")
    lines.append("")
    lines.append("-" * 63)
    lines.append("WHY THE MODEL MADE THIS DECISION")
    lines.append("-" * 63)
    lines.append("")
    lines.append("The CNN analyzed these visible facial regions:")
    lines.append("  • Eye region")
    lines.append("  • Eyebrow shape/tension")
    lines.append("  • Mouth curvature")
    lines.append("  • Overall facial muscle activation")
    lines.append("")
    lines.append("Key visual patterns observed:")
    for obs in observed_patterns:
        lines.append(f"  • {obs}")
    lines.append("")
    lines.append("-" * 63)
    lines.append("MENTAL HEALTH INTERPRETATION")
    lines.append("-" * 63)
    lines.append("")
    lines.append(interpretation)
    lines.append("")
    lines.append("This is not a diagnosis. It is an AI-assisted emotional screening result.")
    lines.append("")
    lines.append("-" * 63)
    lines.append("DISCLAIMER")
    lines.append("-" * 63)
    lines.append("")
    lines.append("This system provides AI-assisted screening only.")
    lines.append("Final assessment must be performed by qualified mental health professionals.")
    lines.append("")
    lines.append("=" * 66)

    return "\n".join(lines)


def _make_keras_compat_custom_objects():
    """Custom layers that strip unknown config keys so .keras saved with newer Keras can load."""
    try:
        import tensorflow as tf
    except ImportError:
        return {}
    # Dense from newer Keras includes quantization_config; older Keras doesn't accept it.
    # Build a new dict so the parent never sees unknown keys (config may be non-mutable).
    _SKIP_KEYS = frozenset({"quantization_config"})

    class DenseCompat(tf.keras.layers.Dense):
        @classmethod
        def from_config(cls, config):
            # Pass only keys the parent Dense accepts (avoid quantization_config, etc.)
            config_clean = {k: v for k, v in dict(config).items() if k not in _SKIP_KEYS}
            return super().from_config(config_clean)
    return {"Dense": DenseCompat}


def load_model(path=None):
    """Load the emotion model. Tries SavedModel dir first (best compatibility), then .keras file.
    Returns (model, error_message). model is None on failure; error_message is set when the reason is known (e.g. TensorFlow not installed)."""
    try:
        import tensorflow as tf
    except ImportError:
        return None, (
            "TensorFlow is not installed. Add 'tensorflow-cpu' to requirements.txt and redeploy, "
            "or run: pip install tensorflow-cpu"
        )
    # Try SavedModel directory first (avoids Keras config version mismatches)
    candidates = (path,) if path else (MODEL_PATH_SAVEDMODEL, MODEL_PATH_KERAS)
    for candidate in candidates:
        if candidate is None:
            continue
        if os.path.isdir(candidate) and os.path.isfile(os.path.join(candidate, "saved_model.pb")):
            try:
                return tf.keras.models.load_model(candidate), None
            except Exception as e:
                return None, f"Failed to load SavedModel from {candidate}: {e}"
        if os.path.isfile(candidate):
            try:
                return tf.keras.models.load_model(candidate), None
            except Exception as e:
                if "quantization_config" in str(e):
                    try:
                        return tf.keras.models.load_model(
                            candidate, custom_objects=_make_keras_compat_custom_objects()
                        ), None
                    except Exception as e2:
                        return None, (
                            f"Model version mismatch. Re-export from notebook: "
                            f"model.export('emotion_model'). Error: {e2}"
                        )
                return None, f"Failed to load model from {candidate}: {e}"
    return None, (
        "Emotion model not found. Export from image_model.ipynb: model.export('emotion_model'), "
        "then add the emotion_model/ folder to your app (e.g. commit it or deploy it)."
    )


def generate_and_save_report(image_bytes_or_path, student_id, report_path=REPORT_PATH):
    """
    Load image, run model (if available), generate report, and save to clinical_report.txt.
    Returns (report_text, error_message). If error_message is set, report_text may be placeholder.
    """
    try:
        image_array = load_and_preprocess_image(image_bytes_or_path)
    except Exception as e:
        return None, f"Failed to load image: {e}"

    model, _load_error = load_model()
    if model is None:
        hint = _load_error or (
            "Export the model from image_model.ipynb: model.export('emotion_model'), "
            "then ensure the emotion_model/ folder is deployed with the app."
        )
        placeholder = (
            "==================================================================\n"
            "AI-ASSISTED MENTAL HEALTH SCREENING REPORT\n"
            "==================================================================\n\n"
            f"Student ID: {student_id}\n"
            f"Analysis Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            "----------------------------------------------------------------\n"
            "MODEL PREDICTION\n"
            "----------------------------------------------------------------\n\n"
            f"No model loaded. {hint}\n\n"
            "Then run this app again to generate predictions from your image.\n\n"
            "----------------------------------------------------------------\n"
            "DISCLAIMER\n"
            "----------------------------------------------------------------\n\n"
            "This system provides AI-assisted screening only.\n"
            "Final assessment must be performed by qualified mental health professionals.\n\n"
            "==================================================================\n"
        )
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(placeholder)
        return placeholder, f"Model not loaded. {hint}"

    report_text = generate_report_text(
        image_array, model, DEFAULT_CLASS_NAMES, student_id=student_id
    )
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)
    return report_text, None
