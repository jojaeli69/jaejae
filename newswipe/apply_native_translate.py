from pathlib import Path
source=Path("../newswipe/KeyboardTranslateNative.java")
target=Path("app/src/main/java/com/alternative_studios/newswipe/KeyboardTranslatePanel.java")
assert source.exists() and target.exists()
content=source.read_text(encoding="utf-8")
assert "NewSwipe-native appearance with Samsung Keyboard" in content
assert 'actions.onApplyTranslation(result, originalSelection,selection,selection)' in content
assert 'Ui.chipRadius(getContext())' in content
target.write_text(content,encoding="utf-8")
print("NewSwipe-native skin + direct translation commit source installed")
